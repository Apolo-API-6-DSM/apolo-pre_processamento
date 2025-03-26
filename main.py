from fastapi import FastAPI
from modules.importacao.controller import router as importacao_router
import uvicorn

app = FastAPI(title="API de Processamento de Dados")

# Registra todos os routers
app.include_router(importacao_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )