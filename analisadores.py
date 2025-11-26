# Analisador léxico e analisador semântico sequenciais (sem recursão).


import re

# -------------------------
# TOKEN (estrutura simples)
# -------------------------
class Token:
    def __init__(self, tipo, valor, linha, coluna):
        self.tipo = tipo
        self.valor = valor
        self.linha = linha
        self.coluna = coluna

    def __repr__(self):
        return f"Token({self.tipo}, {self.valor!r}, linha={self.linha}, col={self.coluna})"


# -------------------------
# ANALISADOR LÉXICO
# -------------------------
class AnalisadorLexico:
    """
    Analisador léxico totalmente sequencial (sem recursão).
    Produz uma lista de tokens com linha/coluna.
    Mensagens de erro em português.
    """

    PALAVRAS_RESERVADAS = {
        "int", "boolean", "procedure",
        "if", "else", "while",
        "return", "break", "continue",
        "print", "true", "false"
    }

    # padrões, testados sequencialmente sobre o texto
    PADROES = [
        ("NUM",    r"\d+"),
        ("ID",     r"[A-Za-z_][A-Za-z0-9_]*"),
        ("OP",     r"==|!=|>=|<=|[+\-*/<>]"),
        ("ATRIB",  r"="),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("VIRG",   r","),
        ("PTO_V",  r";"),
        ("WS",     r"[ \t\r]+"),
        ("NL",     r"\n"),
        ("OUTRO",  r"."),
    ]
    REGEX = re.compile("|".join(f"(?P<{n}>{p})" for n, p in PADROES))

    def __init__(self, codigo):
        self.codigo = codigo
        self.tokens = []
        self.linha = 1
        self.coluna = 1

    def analisar(self):
        """Executa a varredura léxica de forma sequencial."""
        for m in self.REGEX.finditer(self.codigo):
            tipo = m.lastgroup
            txt = m.group()
            if tipo == "NUM":
                self.tokens.append(Token("NUM", int(txt), self.linha, self.coluna))
            elif tipo == "ID":
                if txt in self.PALAVRAS_RESERVADAS:
                    self.tokens.append(Token(txt.upper(), txt, self.linha, self.coluna))
                else:
                    self.tokens.append(Token("ID", txt, self.linha, self.coluna))
            elif tipo == "OP":
                self.tokens.append(Token("OP", txt, self.linha, self.coluna))
            elif tipo == "ATRIB":
                self.tokens.append(Token("ATRIB", txt, self.linha, self.coluna))
            elif tipo in ("LPAREN","RPAREN","LBRACE","RBRACE","VIRG","PTO_V"):
                self.tokens.append(Token(tipo, txt, self.linha, self.coluna))
            elif tipo == "WS":
                # apenas avança coluna
                pass
            elif tipo == "NL":
                self.linha += 1
                self.coluna = 0
            elif tipo == "OUTRO":
                raise Exception(f"Erro léxico: símbolo inválido '{txt}' na linha {self.linha}, coluna {self.coluna}")
            self.coluna += len(txt)
        self.tokens.append(Token("EOF", None, self.linha, self.coluna))
        return self.tokens


# -------------------------
# ANALISADOR SEMÂNTICO 
# -------------------------
class ErroSemantico(Exception):
    pass

class AnalisadorSemantico:
   
    def __init__(self):
        # tabelas (ambiente global simples)
        self.tabela_funcoes = {}     # nome -> (tipo_retorno, params_list)
        self.tabela_proceds = {}     # nome -> params_list

        # pilha de escopos (cada item é dict de variáveis); começamos com escopo global
        self.escopos = [ {} ]  # cada escopo: nome -> tipo

    # ---------- utilitários de escopo (sequencial) ----------
    def abrir_escopo(self):
        self.escopos.append({})

    def fechar_escopo(self):
        if len(self.escopos) == 1:
            # nunca remover o escopo global
            return
        self.escopos.pop()

    def declarar_variavel_atual(self, nome, tipo, linha=None, coluna=None):
        escopo_atual = self.escopos[-1]
        if nome in escopo_atual:
            raise ErroSemantico(f"Erro semântico: variável '{nome}' já declarada no mesmo escopo (linha {linha}, col {coluna})")
        escopo_atual[nome] = tipo

    def buscar_variavel(self, nome):
        # procura do escopo mais interno ao mais externo
        for esc in reversed(self.escopos):
            if nome in esc:
                return esc[nome]
        return None

    # ---------- registro de funções/procedimentos ----------
    def registrar_funcao(self, nome, tipo_retorno, params, linha=None, coluna=None):
        if nome in self.tabela_funcoes or nome in self.tabela_proceds:
            raise ErroSemantico(f"Erro semântico: função/procedimento '{nome}' já declarado (linha {linha}, col {coluna})")
        self.tabela_funcoes[nome] = (tipo_retorno, params)

    def registrar_procedimento(self, nome, params, linha=None, coluna=None):
        if nome in self.tabela_funcoes or nome in self.tabela_proceds:
            raise ErroSemantico(f"Erro semântico: função/procedimento '{nome}' já declarado (linha {linha}, col {coluna})")
        self.tabela_proceds[nome] = params

    # ---------- verificação de tipos em expressões (sequencial) ----------
    def avaliar_expressao_tipo(self, expr):
        """
        Recebe uma representação simples de expressão e retorna tipo 'int' ou 'boolean'.
        Formatos esperados (simples):
         - {"kind":"lit","tipo":"int","valor":N}
         - {"kind":"lit","tipo":"boolean","valor":True}
         - {"kind":"var","nome":"x"}
         - {"kind":"binop","op":"+","left":..., "right":...}
         - {"kind":"call","nome":"f","args":[...]}
         - {"kind":"unop","op":"!","expr": ...}  (opcional)
        """
        if expr is None:
            raise ErroSemantico("Erro semântico: expressão vazia")

        k = expr.get("kind")
        if k == "lit":
            return expr["tipo"]
        if k == "var":
            tipo = self.buscar_variavel(expr["nome"])
            if tipo is None:
                raise ErroSemantico(f"Erro semântico: variável '{expr['nome']}' usada sem declaração (linha {expr.get('linha')})")
            return tipo
        if k == "unop":
            op = expr.get("op")
            t = self.avaliar_expressao_tipo(expr["expr"])
            if op == "!" :
                if t != "boolean":
                    raise ErroSemantico(f"Erro semântico: operador unário '!' exige boolean")
                return "boolean"
            raise ErroSemantico(f"Erro semântico: operador unário desconhecido '{op}'")
        if k == "binop":
            op = expr["op"]
            tleft = self.avaliar_expressao_tipo(expr["left"])
            tright = self.avaliar_expressao_tipo(expr["right"])
            # operadores aritméticos -> int, operadores relacionais -> boolean
            if op in ("+", "-", "*", "/"):
                if tleft != "int" or tright != "int":
                    raise ErroSemantico(f"Erro semântico: operador '{op}' exige operandos int")
                return "int"
            if op in ("==", "!=", ">", "<", ">=", "<="):
                # permitimos comparações entre mesmos tipos (int/boolean), mas geralmente ints
                if tleft != tright:
                    raise ErroSemantico(f"Erro semântico: comparação entre tipos diferentes ({tleft} vs {tright})")
                return "boolean"
            if op in ("&&","||"):
                if tleft != "boolean" or tright != "boolean":
                    raise ErroSemantico(f"Erro semântico: operador '{op}' exige operandos booleanos")
                return "boolean"
            raise ErroSemantico(f"Erro semântico: operador desconhecido '{op}'")
        if k == "call":
            # checa chamada em expressão (função obrigatória)
            return self._checar_chamada_em_expressao(expr)
        raise ErroSemantico(f"Erro semântico: expressão inválida/nao suportada: {expr}")

    def _checar_chamada_em_expressao(self, expr):
        nome = expr["nome"]
        args = expr.get("args", [])
        if nome in self.tabela_funcoes:
            tipo_retorno, params = self.tabela_funcoes[nome]
            if len(params) != len(args):
                raise ErroSemantico(f"Erro semântico: chamada a função '{nome}' com número errado de argumentos")
            # checar tipos dos args
            for idx, arg in enumerate(args):
                t = self.avaliar_expressao_tipo(arg)
                esperado = params[idx][0]
                if t != esperado:
                    raise ErroSemantico(f"Erro semântico: argumento {idx+1} de '{nome}' tem tipo {t}, esperado {esperado}")
            return tipo_retorno
        if nome in self.tabela_proceds:
            raise ErroSemantico(f"Erro semântico: procedimento '{nome}' não retorna valor (usado em expressão)")
        raise ErroSemantico(f"Erro semântico: função/procedimento '{nome}' não declarada")

    def _checar_chamada_como_comando(self, nome, args, linha=None):
        # chamada usada como comando (pode ser procedimento OU função — aceitamos função-valor descartado)
        if nome in self.tabela_funcoes:
            tipo_retorno, params = self.tabela_funcoes[nome]
            if len(params) != len(args):
                raise ErroSemantico(f"Erro semântico: chamada a função '{nome}' com número errado de argumentos (linha {linha})")
            for i, a in enumerate(args):
                ta = self.avaliar_expressao_tipo(a)
                esperado = params[i][0]
                if ta != esperado:
                    raise ErroSemantico(f"Erro semântico: argumento {i+1} de '{nome}' tem tipo {ta}, esperado {esperado} (linha {linha})")
            # chamada de função como comando -> permitida (valor descartado)
            return
        if nome in self.tabela_proceds:
            params = self.tabela_proceds[nome]
            if len(params) != len(args):
                raise ErroSemantico(f"Erro semântico: chamada a procedimento '{nome}' com número errado de argumentos (linha {linha})")
            for i, a in enumerate(args):
                ta = self.avaliar_expressao_tipo(a)
                esperado = params[i][0]
                if ta != esperado:
                    raise ErroSemantico(f"Erro semântico: argumento {i+1} de '{nome}' tem tipo {ta}, esperado {esperado} (linha {linha})")
            return
        raise ErroSemantico(f"Erro semântico: chamada a função/procedimento não declarado '{nome}' (linha {linha})")

    # ---------- checagem sequencial do programa ----------
    def checar_programa(self, lista_de_elementos):
        """
        Percorre sequencialmente os elementos (declarações e comandos)
        e realiza as verificações semânticas.
        """
        # limpa ambiente
        self.tabela_funcoes.clear()
        self.tabela_proceds.clear()
        self.escopos = [ {} ]

        # registrar assinaturas de funções/procedimentos e variáveis globais (primeiro passe)
        for elem in lista_de_elementos:
            kind = elem.get("kind")
            if kind == "vardecl":
                nome = elem["nome"]
                tipo = elem["tipo"]
                if nome in self.escopos[0]:
                    raise ErroSemantico(f"Erro semântico: variável global '{nome}' já declarada (linha {elem.get('linha')})")
                self.escopos[0][nome] = tipo
            elif kind == "funcdecl":
                nome = elem["nome"]
                tipo_ret = elem["tipo"]
                params = elem.get("params", [])
                self.registrar_funcao(nome, tipo_ret, params, elem.get("linha"))
            elif kind == "procdecl":
                nome = elem["nome"]
                params = elem.get("params", [])
                self.registrar_procedimento(nome, params, elem.get("linha"))

        # segundo passe: verificar elementos, corpos, uso
        # rastreia quais funcbodies/procbodies foram encontrados
        funcbodies_encontrados = set()
        procbodies_encontrados = set()

        for elem in lista_de_elementos:
            kind = elem.get("kind")
            if kind == "vardecl":
                # checa inicialização se houver
                if "expr" in elem and elem["expr"] is not None:
                    t = self.avaliar_expressao_tipo(elem["expr"])
                    if t != elem["tipo"]:
                        raise ErroSemantico(f"Erro semântico: inicialização de '{elem['nome']}' tem tipo {t}, esperado {elem['tipo']} (linha {elem.get('linha')})")
            elif kind == "assign":
                self._checar_assign(elem)
            elif kind == "call":
                nome = elem["nome"]
                args = elem.get("args", [])
                self._checar_chamada_como_comando(nome, args, elem.get("linha"))
            elif kind == "funcbody":
                nome = elem["nome"]
                params = elem.get("params", [])
                if nome not in self.tabela_funcoes:
                    raise ErroSemantico(f"Erro semântico: corpo de função '{nome}' sem declaração prévia (linha {elem.get('linha')})")
                funcbodies_encontrados.add(nome)
                self._checar_corpo_funcional(elem, is_function=True)
            elif kind == "procbody":
                nome = elem["nome"]
                params = elem.get("params", [])
                if nome not in self.tabela_proceds:
                    raise ErroSemantico(f"Erro semântico: corpo de procedimento '{nome}' sem declaração prévia (linha {elem.get('linha')})")
                procbodies_encontrados.add(nome)
                self._checar_corpo_funcional(elem, is_function=False)
            elif kind in ("if", "while"):
                # casos soltos no topo (por exemplo em main como comandos globais)
                tcond = self.avaliar_expressao_tipo(elem["cond"])
                if tcond != "boolean":
                    raise ErroSemantico(f"Erro semântico: condição de {kind} não é boolean (linha {elem.get('linha')})")
                # checar body
                for cmd in elem.get("body", []):
                    self.checar_elemento(cmd)
                # else opcional
                if kind == "if" and "else" in elem and elem["else"] is not None:
                    for cmd in elem["else"]:
                        self.checar_elemento(cmd)
            else:
                # fallback: outros comandos
                self.checar_elemento(elem)

        # verificar funções declaradas que não possuem corpo
        for fname in self.tabela_funcoes:
            if fname not in funcbodies_encontrados:
                raise ErroSemantico(f"Erro semântico: função '{fname}' declarada sem corpo/implementação")
        for pname in self.tabela_proceds:
            if pname not in procbodies_encontrados:
                # aceitável se procedimentos podem ficar sem corpo? A gramática original coloca declarações e corpos separados.
                # aqui exigimos corpo para todas as declarações.
                raise ErroSemantico(f"Erro semântico: procedimento '{pname}' declarado sem corpo/implementação")

    # ---------- helpers ----------
    def _checar_assign(self, elem):
        nome = elem["nome"]
        tvar = self.buscar_variavel(nome)
        if tvar is None:
            raise ErroSemantico(f"Erro semântico: atribuição para variável não declarada '{nome}' (linha {elem.get('linha')})")
        texpr = self.avaliar_expressao_tipo(elem["expr"])
        if tvar != texpr:
            raise ErroSemantico(f"Erro semântico: atribuição tipo mismatch: {tvar} <- {texpr} (linha {elem.get('linha')})")

    def _checar_corpo_funcional(self, elem, is_function):
        """
        Verifica o corpo de função/procedimento:
          - abre escopo
          - declara parâmetros
          - processa comandos sequencialmente (permite vardecl local)
          - para funções: garante pelo menos um return compatível
          - para procedimentos: garante que não haja return com expressão
        """
        nome = elem["nome"]
        params = elem.get("params", [])
        body = elem.get("body", [])

        self.abrir_escopo()
        # declara parâmetros
        for tipo, pname in params:
            self.declarar_variavel_atual(pname, tipo, linha=elem.get("linha"))

        encontrou_return = False

        for cmd in body:
            k = cmd.get("kind")
            if k == "vardecl":
                # declaração local
                tipo = cmd["tipo"]
                vnome = cmd["nome"]
                self.declarar_variavel_atual(vnome, tipo, linha=cmd.get("linha"))
                if "expr" in cmd and cmd["expr"] is not None:
                    tinit = self.avaliar_expressao_tipo(cmd["expr"])
                    if tinit != tipo:
                        raise ErroSemantico(f"Erro semântico: inicialização de '{vnome}' tem tipo {tinit}, esperado {tipo} (linha {cmd.get('linha')})")
            elif k == "assign":
                self._checar_assign(cmd)
            elif k == "call":
                self._checar_chamada_como_comando(cmd["nome"], cmd.get("args", []), cmd.get("linha"))
            elif k == "return":
                encontrou_return = True
                if not is_function:
                    # procedimento não deve retornar valor
                    raise ErroSemantico(f"Erro semântico: 'return' em procedimento '{nome}' (linha {cmd.get('linha')})")
                tipo_ret_esperado = self.tabela_funcoes[nome][0]
                texpr = self.avaliar_expressao_tipo(cmd["expr"])
                if texpr != tipo_ret_esperado:
                    raise ErroSemantico(f"Erro semântico: retorno de '{nome}' tem tipo {texpr}, esperado {tipo_ret_esperado} (linha {cmd.get('linha')})")
            elif k == "if":
                tcond = self.avaliar_expressao_tipo(cmd["cond"])
                if tcond != "boolean":
                    raise ErroSemantico(f"Erro semântico: condição de if não é boolean (linha {cmd.get('linha')})")
                # checar blocos do if (cria escopo temporário para cada bloco)
                self.abrir_escopo()
                for c in cmd.get("body", []):
                    self.checar_elemento(c)
                self.fechar_escopo()
                if "else" in cmd and cmd["else"] is not None:
                    self.abrir_escopo()
                    for c in cmd.get("else", []):
                        self.checar_elemento(c)
                    self.fechar_escopo()
            elif k == "while":
                tcond = self.avaliar_expressao_tipo(cmd["cond"])
                if tcond != "boolean":
                    raise ErroSemantico(f"Erro semântico: condição de while não é boolean (linha {cmd.get('linha')})")
                self.abrir_escopo()
                for c in cmd.get("body", []):
                    self.checar_elemento(c)
                self.fechar_escopo()
            elif k == "print":
                # print(expr);
                te = self.avaliar_expressao_tipo(cmd["expr"])
                # aceita int ou boolean (conforme gramática)
            elif k == "jump":
                # jump: {'kind':'jump', 'op':'break'|'continue', 'linha':...}
                op = cmd.get("op")
                if op not in ("break", "continue"):
                    raise ErroSemantico(f"Erro semântico: jump desconhecido '{op}' (linha {cmd.get('linha')})")
            else:
                # fallback: checar outros elementos via checar_elemento
                self.checar_elemento(cmd)

        self.fechar_escopo()

        if is_function and not encontrou_return:
            raise ErroSemantico(f"Erro semântico: função '{nome}' sem retorno (return) no corpo (linha {elem.get('linha')})")

    def checar_elemento(self, elem):
        """Checagem auxiliar para elementos isolados (usado recursivamente de forma controlada)."""
        kind = elem.get("kind")
        if kind == "assign":
            self._checar_assign(elem)
        elif kind == "call":
            self._checar_chamada_como_comando(elem["nome"], elem.get("args", []), elem.get("linha"))
        elif kind == "vardecl":
            # declaração local em contexto onde checar_elemento é chamado
            tipo = elem["tipo"]
            nome = elem["nome"]
            self.declarar_variavel_atual(nome, tipo, linha=elem.get("linha"))
            if "expr" in elem and elem["expr"] is not None:
                tinit = self.avaliar_expressao_tipo(elem["expr"])
                if tinit != tipo:
                    raise ErroSemantico(f"Erro semântico: inicialização de '{nome}' tem tipo {tinit}, esperado {tipo} (linha {elem.get('linha')})")
        elif kind == "if":
            tcond = self.avaliar_expressao_tipo(elem["cond"])
            if tcond != "boolean":
                raise ErroSemantico(f"Erro semântico: condição de if não é boolean (linha {elem.get('linha')})")
            # checar corpo e else com escopos temporários
            self.abrir_escopo()
            for c in elem.get("body", []):
                self.checar_elemento(c)
            self.fechar_escopo()
            if "else" in elem and elem["else"] is not None:
                self.abrir_escopo()
                for c in elem.get("else", []):
                    self.checar_elemento(c)
                self.fechar_escopo()
        elif kind == "while":
            tcond = self.avaliar_expressao_tipo(elem["cond"])
            if tcond != "boolean":
                raise ErroSemantico(f"Erro semântico: condição de while não é boolean (linha {elem.get('linha')})")
            self.abrir_escopo()
            for c in elem.get("body", []):
                self.checar_elemento(c)
            self.fechar_escopo()
        elif kind == "print":
            _ = self.avaliar_expressao_tipo(elem["expr"])
        elif kind == "jump":
            op = elem.get("op")
            if op not in ("break", "continue"):
                raise ErroSemantico(f"Erro semântico: jump desconhecido '{op}' (linha {elem.get('linha')})")
        elif kind == "return":
            # return fora de função/procedure: será verificado ao entrar no corpo
            raise ErroSemantico(f"Erro semântico: 'return' fora de função/procedimento (linha {elem.get('linha')})")
        else:
            # outros possíveis kinds podem ser ignorados/expandidos
            pass



# -------------------------
# EXEMPLO DE USO
# -------------------------
if __name__ == "__main__":
    # exemplo de código-fonte simples (para testar o léxico)
    codigo = """
    int x;
    int soma(int a, int b) { 
       return a + b;
    }
    x = soma(3, 4);
    print x;
    """

    print("== LEXER ==")
    lex = AnalisadorLexico(codigo)
    toks = lex.analisar()
    for t in toks:
        print(t)

    print("\n== SEMÂNTICO (exemplo de representação linear) ==")
    # Representação didática do programa (normalmente produzida pelo parser)
    programa = [
        {"kind":"vardecl","tipo":"int","nome":"x","linha":2},
        {"kind":"funcdecl","nome":"soma","tipo":"int","params":[("int","a"),("int","b")],"linha":3},
        {"kind":"funcbody","nome":"soma","params":[("int","a"),("int","b")],
         "body":[
             {"kind":"return","expr":{"kind":"binop","op":"+",
                                      "left":{"kind":"var","nome":"a"},
                                      "right":{"kind":"var","nome":"b"}}}
         ]},
        {"kind":"assign","nome":"x","expr":{"kind":"call","nome":"soma","args":[
            {"kind":"lit","tipo":"int","valor":3},
            {"kind":"lit","tipo":"int","valor":4}
        ]},"linha":6},
        {"kind":"call","nome":"print","args":[{"kind":"var","nome":"x"}],"linha":7}
    ]

    sem = AnalisadorSemantico()
    try:
        sem.checar_programa(programa)
        print("Semântico: sem erros detectados")
    except Exception as e:
        print("Erro semântico detectado:", e)