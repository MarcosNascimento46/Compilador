from lexer import AnalisadorLexico
from semantic import AnalisadorSemantico, ErroSemantico

if __name__ == "__main__":
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
    tokens = lex.analisar()
    for t in tokens:
        print(t)

    print("\n== SEMÂNTICO ==")

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
    except ErroSemantico as e:
        print("Erro semântico:", e)
