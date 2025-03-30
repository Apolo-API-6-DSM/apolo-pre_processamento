# 🐍 apolo-pre-processamento

Scripts Python para pré-processamento de datasets

## 📋 Pré-requisitos

- Python 3.10+
- MongoDB (opcional, se usar conexão com banco)
- Git (opcional)

## 🛠️ Configuração

1. **Clone o repositório**
    ```bash
    git clone [https://github.com/Apolo-API-6-DSM/apolo-pre_processamento]
    cd apolo-pre-processamento

2. **Configure as variáveis de ambiente**
    ```bash
    MONGO_URI=""
    MONGODB_DBNAME="nome_do_banco"
    API_PORT=8000
    
3. **Execução**

    **Opção 1: Sem ambiente virtual (mais simples)**
        ```bash
        # Instale as dependências globalmente
        pip install -r requirements.txt

        # Execute o script principal
        python main.py

    **Opção 2: Com ambiente virtual (recomendado)**
        ```bash
        # Crie o ambiente virtual
        python -m venv venv

        # Ative o ambiente
        # Linux/MacOS:
        source venv/bin/activate
        # Windows:
        .\venv\Scripts\activate

        # Instale as dependências
        pip install -r requirements.txt

        # Execute o script
        python main.py

        # Para desativar o ambiente depois
        deactivate


## 📂 Estrutura do Projeto
```text
apolo-pre-processamento/
├── modules/
│   ├── anonimo/               
│   ├── importacao/            
│   ├── tratamento_descricao_dataset/  
│   ├── tratamento_mensagem/    
│   └── shared/                 
├── tests/                      
├── venv/                       
├── .env                        
├── app.log                     
├── debug.py                    
├── main.py                     
└── requirements.txt            