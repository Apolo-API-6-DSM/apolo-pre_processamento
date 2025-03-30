from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from modules.shared.database import get_db
from modules.shared.logger import logger
from modules.tratamento_mensagem.service import limpar_mensagem
from modules.nova_tabela_descricao_dataset.service import extrair_descricao
from modules.tratamento_descricao_dataset.service import limpar_descricao
from modules.anonimo.service import Anonimizador
import requests

router = APIRouter(prefix="/api/v1")

LOTE_TAMANHO = 10

@router.post("/process")
async def process_ids(request: Request, background_tasks: BackgroundTasks):
    """Endpoint para receber IDs e iniciar processamento"""
    try:
        data = await request.json()
        ids = data.get('ids', []) if isinstance(data, dict) else data
        
        if not isinstance(ids, list):
            raise ValueError("Formato inválido. Esperado lista de IDs")
        
        if not ids:
            logger.info("Nenhum ID foi enviado para processamento.")
            return {"status": "success", "message": "Nenhum ID para processar"}
        
        logger.info(f"Recebido {len(ids)} IDs para processamento. Iniciando o processamento em background.")
        
        # Adiciona o processamento em segundo plano
        background_tasks.add_task(processar_e_obter_descricoes, ids)
        
        logger.info("Processamento adicionado à fila de tarefas do BackgroundTasks.")
        
        return {
            "status": "success",
            "message": "Processamento iniciado em background.",
            "received_ids": len(ids)
        }
    
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))


def processar_e_obter_descricoes(ids: list):
    """Processa os IDs e retorna lista de dicionários com chamadoId e descricao_dataset"""
    db = get_db()
    chamados = []
    
    logger.info(f"Iniciando processamento detalhado de {len(ids)} IDs no MongoDB.")
    
    items = list(db["interacoes"].find({"chamadoId": {"$in": ids}}))
    
    if not items:
        logger.warning("Nenhum item encontrado no banco de dados para os IDs fornecidos.")
        return
    
    for item in items:
        try:
            if not item:
                continue
            
            chamado_id = item.get('chamadoId')
            
            processado = db["interacoes_processadas"].find_one({"chamadoId": chamado_id})
            if processado and processado.get("emocao") and processado.get("tipoChamado"):
                logger.info(f"ChamadoId {chamado_id} já foi processado anteriormente. Pulando...")
                continue 

            logger.info(f"Processando chamadoId: {chamado_id}")
            
            mensagem_limpa = limpar_mensagem(item.get("mensagem", ""))
            descricao = extrair_descricao(mensagem_limpa)
            descricao_limpa = limpar_descricao(descricao) if descricao else ""
            
            if descricao_limpa:
                descricao_limpa = Anonimizador().anonimizar_texto(descricao_limpa)
            
            db["interacoes_processadas"].update_one(
                {"chamadoId": chamado_id},
                {"$set": {
                    "mensagem_limpa": mensagem_limpa,
                    "descricao_dataset": descricao_limpa
                }},
                upsert=True
            )
            
            logger.info(f"ChamadoId {chamado_id} processado e salvo no banco de dados.")
            
            chamados.append({
                "chamadoId": chamado_id,
                "descricao": descricao_limpa
            })
            
            if len(chamados) >= LOTE_TAMANHO:
                enviar_para_previsao(chamados)
                chamados.clear()
            
        except Exception as e:
            logger.error(f"Erro processando item {item.get('chamadoId')}: {str(e)}")
            continue

    if chamados:
        enviar_para_previsao(chamados)


def enviar_para_previsao(chamados: list):
    """Envia os chamados para o Flask para análise de sentimentos"""
    try:
        logger.info(f"Enviando {len(chamados)} chamados para análise de emoções no Flask.")
        
        response = requests.post(
            "http://localhost:8080/prever",
            json={"chamados": chamados},
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        response.raise_for_status()
        
        logger.info(f"Lote enviado com sucesso! Resposta: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Erro ao enviar lote para Flask: {str(e)}")

@router.post("/processar-teste")
async def processar_teste(request: Request):
    """Endpoint para testar o processamento de um único ID"""
    try:
        data = await request.json()
        chamado_id = data.get("chamadoId")
        
        if not chamado_id:
            raise HTTPException(status_code=400, detail="ID do chamado não fornecido.")

        logger.info(f"Recebendo chamadoId {chamado_id} para teste.")

        # Processa o chamado individualmente
        resultado = processar_individualmente(chamado_id)
        
        if not resultado:
            raise HTTPException(status_code=404, detail=f"ChamadoId {chamado_id} não encontrado no banco de dados.")
        
        # Envia o chamado para análise
        enviar_para_previsao([resultado])

        return {
            "status": "success",
            "message": f"ChamadoId {chamado_id} processado e enviado para análise."
        }
    
    except Exception as e:
        logger.error(f"Erro ao processar chamadoId {chamado_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


def processar_individualmente(chamado_id: str):
    """Processa um único chamado pelo chamadoId"""
    db = get_db()
    item = db["interacoes"].find_one({"chamadoId": chamado_id})
    
    if not item:
        logger.warning(f"ChamadoId {chamado_id} não encontrado no banco de dados.")
        return None
    
    try:
        logger.info(f"Processando chamadoId: {chamado_id}")
        
        mensagem_limpa = limpar_mensagem(item.get("mensagem", ""))
        descricao = extrair_descricao(mensagem_limpa)
        descricao_limpa = limpar_descricao(descricao) if descricao else ""
        
        if descricao_limpa:
            descricao_limpa = Anonimizador().anonimizar_texto(descricao_limpa)
        
        # Atualiza o MongoDB com o dado processado
        db["interacoes_processadas"].update_one(
            {"chamadoId": chamado_id},
            {"$set": {
                "mensagem_limpa": mensagem_limpa,
                "descricao_dataset": descricao_limpa
            }},
            upsert=True
        )
        
        logger.info(f"ChamadoId {chamado_id} processado e salvo no banco de dados.")

        return {
            "chamadoId": chamado_id,
            "descricao": descricao_limpa
        }
        
    except Exception as e:
        logger.error(f"Erro processando item {chamado_id}: {str(e)}")
        return None