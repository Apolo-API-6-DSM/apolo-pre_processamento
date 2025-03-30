from fastapi import FastAPI, HTTPException, Request
from pymongo import MongoClient
from dotenv import load_dotenv
from pydantic import BaseModel
import os
import uvicorn
import logging
from typing import List, Dict, Optional

# Configuração
load_dotenv()
app = FastAPI()

# Modelo Pydantic para validação
class ProcessRequest(BaseModel):
    ids: List[str]
    collection: Optional[str] = "interacoes"  # Parâmetro opcional

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conexão com MongoDB Atlas
def get_db():
    return MongoClient(os.getenv("MONGO_URI"))

@app.on_event("startup")
async def startup_db_client():
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client[os.getenv("MONGODB_DBNAME")]
        # Testa a conexão
        db.command('ping')
        logger.info("✅ Conectado ao MongoDB com sucesso")
        # Verifica se a coleção existe
        if "interacoes" not in db.list_collection_names():
            logger.error("❌ Coleção 'interacoes' não encontrada")
    except Exception as e:
        logger.error(f"❌ Falha na conexão com MongoDB: {str(e)}")
        raise

@app.post("/api/v1/process")
async def process_ids(request: Request):
    """Endpoint mais tolerante para receber IDs"""
    try:
        # Aceita tanto o formato Pydantic quanto um JSON bruto
        data = await request.json()
        
        # Extrai os IDs independentemente do formato
        if isinstance(data, dict) and 'ids' in data:
            ids = data['ids']
        elif isinstance(data, list):
            ids = data
        else:
            raise ValueError("Formato inválido. Esperado {'ids': [...]} ou lista de IDs")
        
        logger.info(f"Recebidos {len(ids)} IDs para processamento")
        
        return {
            "status": "success",
            "received_ids": len(ids),
            "sample_ids": ids[:5]
        }
    
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Formato de dados inválido. Detalhes: {str(e)}"
        )

@app.get("/api/v1/items/{item_id}")
async def get_item(item_id: str):
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client[os.getenv("MONGODB_DBNAME")]
        
        logger.info(f"Buscando ID: {item_id}")
        
        # Verifica primeiro se o ID existe
        if not db["interacoes"].find_one({"chamadoId": item_id}):
            logger.error(f"ID {item_id} não encontrado na coleção")
            # Verifica os primeiros 5 itens para debug
            sample_items = list(db["interacoes"].find().limit(5))
            logger.info(f"Exemplo de itens no MongoDB: {[item['chamadoId'] for item in sample_items]}")
            
            raise HTTPException(
                status_code=404,
                detail=f"Item não encontrado. IDs existentes começam com: {[item['chamadoId'] for item in sample_items][:3]}..."
            )
        
        item = db["interacoes"].find_one(
            {"chamadoId": item_id},
            {"_id": 0}  # Remove o campo _id do resultado
        )
        
        return {
            "status": "success",
            "data": item
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no MongoDB: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro no servidor ao buscar o item: {str(e)}"
        )

if __name__ == "__main__":
    logger.info("Iniciando servidor FastAPI na porta 8000")
    uvicorn.run(
        "debug:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )