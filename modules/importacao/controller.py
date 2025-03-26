from fastapi import APIRouter, HTTPException, Request
from modules.shared.database import get_db
from modules.shared.logger import logger
from modules.tratamento_mensagem.service import limpar_mensagem
from modules.nova_tabela_descricao_dataset.service import extrair_descricao
from modules.tratamento_descricao_dataset.service import limpar_descricao
from modules.anonimo.service import Anonimizador

router = APIRouter(prefix="/api/v1")

@router.post("/process")
async def process_ids(request: Request):
    """Endpoint para receber IDs e iniciar processamento"""
    try:
        data = await request.json()
        ids = data.get('ids', []) if isinstance(data, dict) else data
        
        if not isinstance(ids, list):
            raise ValueError("Formato inválido. Esperado lista de IDs")
        
        if not ids:  # Verifica lista vazia
            return {
                "status": "success",
                "message": "Nenhum ID para processar",
                "received_ids": 0
            }
        
        logger.info(f"Iniciando processamento para {len(ids)} IDs")
        
        # Processamento em pipeline
        # processar_pipeline(ids)
        # Processa em lotes para evitar timeout
        batch_size = 100
        results = []
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            # processar_batch(batch)  # Função síncrona que processa 100 itens de cada vez
            # logger.info(f"Processado lote {i//batch_size + 1}/{(len(ids)//batch_size)+1}")
            processed = processar_batch(batch)
            results.extend(processed)
            logger.info(f"Processado lote {i//batch_size + 1}/{(len(ids)//batch_size)+1}")
        
        return {
            "status": "success",
            "received_ids": len(ids),
            "processed_items": len(results),
            "processed_batches": (len(ids)//batch_size)+1
        }
    
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))

def processar_batch(batch: list):
    """Processa um lote de 100 itens de cada vez"""
    db = get_db()
    items = list(db["interacoes"].find({"chamadoId": {"$in": batch}}))
    processed_items = []
    
    if not items:  # Verifica se há itens
        return processed_items
    
    for item in items:
        try:
            if not item:  # Verifica item individual
                continue
                
            # Etapa 1: Limpeza da mensagem
            mensagem_limpa = limpar_mensagem(item.get("mensagem", ""))
            item["mensagem_limpa"] = mensagem_limpa
            
            # Etapa 2: Extração da descrição
            descricao = extrair_descricao(mensagem_limpa)
            
            # Etapa 3: Tratamento da descrição
            descricao_limpa = limpar_descricao(descricao) if descricao else ""
            item["descricao_dataset"] = descricao_limpa

            # Etapa Final: Anonimização
            if item["descricao_dataset"]:
                anonimizador = Anonimizador()
                item["descricao_dataset"] = anonimizador.anonimizar_texto(
                    texto=item["descricao_dataset"]
                )
            
            # Atualização no MongoDB
            db["interacoes_processadas"].update_one(
                {"chamadoId": item["chamadoId"]},
                {"$set": item},
                upsert=True
            )
            
            processed_items.append(item["chamadoId"])
            
        except Exception as e:
            logger.error(f"Erro processando item {item.get('chamadoId')}: {str(e)}")
            continue
    
    logger.info(f"Processamento concluído para {len(processed_items)} itens")
    return processed_items  # Retorna a lista de IDs processados
        
def processar_pipeline(ids: list):
    """Orquestra todo o fluxo de processamento"""
    db = get_db()
    
    # 1. Busca os dados no MongoDB
    items = list(db["interacoes"].find({"chamadoId": {"$in": ids}}))
    
    # 2. Aplica tratamento de mensagem
    for item in items:
        item["mensagem_limpa"] = limpar_mensagem(item.get("mensagem", ""))
        
        # Aqui você adicionará as próximas etapas:
        # 3. nova_tabela_descricao_dataset
        # 4. tratamento_descricao_dataset
        # 5. anonimo
        
        # Atualiza no MongoDB
        db["interacoes_processadas"].update_one(
            {"chamadoId": item["chamadoId"]},
            {"$set": item},
            upsert=True
        )
    
    logger.info(f"Processamento concluído para {len(items)} itens")