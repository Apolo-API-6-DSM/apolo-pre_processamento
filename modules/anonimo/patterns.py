from presidio_analyzer import Pattern

PADROES_PERSONALIZADOS = [
    {
        "entidade": "CPF",
        "padroes": [
            Pattern(name="cpf_formatado", regex=r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", score=0.9),
            Pattern(name="cpf_simples", regex=r"\b\d{11}\b", score=0.85)
        ],
        "contexto": ["CPF", "documento", "cadastro", "número"]
    },
    {
        "entidade": "EMAIL",
        "padroes": [
            Pattern(name="email_simples", regex=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", score=0.95)
        ],
        "contexto": ["e-mail", "contato", "enviar para"]
    },
    {
        "entidade": "TELEFONE",
        "padroes": [
            Pattern(name="telefone_formatado", regex=r"\(\d{2}\)\s?\d{4,5}-\d{4}", score=0.9),
            Pattern(name="telefone_simples", regex=r"\b\d{10,11}\b", score=0.8)
        ],
        "contexto": ["telefone", "celular", "contato"]
    }
]