from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from modules.shared.database import get_db
from modules.shared.logger import logger
from modules.tratamento_mensagem.service import limpar_mensagem
from modules.nova_tabela_descricao_dataset.service import extrair_descricao
from modules.tratamento_descricao_dataset.service import limpar_descricao
from modules.anonimo.service import Anonimizador
import requests

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
                "received_ids": 0,
                "chamados": []
            }
        
        logger.info(f"Iniciando processamento para {len(ids)} IDs")
        
        chamados_processados = processar_e_obter_descricoes(ids)
        resultados = obter_previsoes(chamados_processados)

        batch_size = 100
        results = []
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            processed = processar_batch(batch)
            results.extend(processed)
            logger.info(f"Processado lote {i//batch_size + 1}/{(len(ids)//batch_size)+1}")

        return {
            "status": "success",
            "received_ids": len(ids),
            "processed_items": len(results),
            "processed_batches": (len(ids)//batch_size)+1,
            "message": "Processamento completo. Envio de IDs para previsão em background.",
            "chamados": resultados
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

def enviar_ids_para_previsao(ids: list):
    """Função para enviar IDs para o serviço de previsão (não-bloqueante)"""
    try:
        url = "http://localhost:8080/prever"
        response = requests.post(
            url,
            json={"ids": ids},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"IDs enviados para previsão. Resposta: {response.status_code}")
    except Exception as e:
        logger.error(f"Erro ao enviar IDs para previsão: {str(e)}")
        

@router.post("/enviar-ids")
async def enviar_ids_manual(request: Request):
    """Endpoint para teste manual no Postman"""
    try:
        data = await request.json()
        ids = data.get('ids', [])
        
        if not ids:
            return {"status": "error", "message": "Nenhum ID fornecido"}
        
        # 1. Busca as descrições processadas no MongoDB
        chamados_processados = buscar_descricoes_processadas(ids)
        
        if not chamados_processados:
            return {
                "status": "success",
                "message": "Nenhum dado processado encontrado para os IDs fornecidos",
                "chamados": []
            }
        
        # 2. Envia para o serviço de previsão
        resultado_previsao = enviar_para_previsao(chamados_processados)
        
        return {
            "status": "success",
            "message": f"{len(chamados_processados)} chamados processados enviados para análise",
            "chamados": resultado_previsao.get("chamados", [])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def buscar_descricoes_processadas(ids: list):
    """Busca no MongoDB as descrições já processadas"""
    db = get_db()
    chamados = []
    
    try:
        # Busca apenas os campos necessários
        itens = db["interacoes_processadas"].find(
            {"chamadoId": {"$in": ids}},
            {"chamadoId": 1, "descricao_dataset": 1, "_id": 0}
        )
        
        for item in itens:
            if item.get("descricao_dataset"):
                chamados.append({
                    "chamadoId": item["chamadoId"],
                    "descricao": item["descricao_dataset"]
                })
        
        logger.info(f"Encontrados {len(chamados)} chamados processados")
        return chamados
    
    except Exception as e:
        logger.error(f"Erro ao buscar descrições processadas: {str(e)}")
        return []

def enviar_para_previsao(chamados: list):
    """Envia para o endpoint de previsão e retorna a resposta"""
    try:
        response = requests.post(
            "http://localhost:8080/prever",
            json={"chamados": chamados},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao enviar para previsão: {str(e)}")
        return {
            "chamados": [{
                "chamadoId": c["chamadoId"],
                "descricao": c["descricao"],
                "emocao": "erro_na_analise"
            } for c in chamados]
        }

def processar_e_obter_descricoes(ids: list):
    """Processa os IDs e retorna lista de dicionários com chamadoId e descricao_dataset"""
    db = get_db()
    chamados = []
    
    # Busca os itens no MongoDB
    items = list(db["interacoes"].find({"chamadoId": {"$in": ids}}))
    
    for item in items:
        try:
            if not item:
                continue
                
            # Processamento completo
            mensagem_limpa = limpar_mensagem(item.get("mensagem", ""))
            descricao = extrair_descricao(mensagem_limpa)
            descricao_limpa = limpar_descricao(descricao) if descricao else ""
            
            if descricao_limpa:
                descricao_limpa = Anonimizador().anonimizar_texto(descricao_limpa)
            
            # Atualiza no MongoDB
            db["interacoes_processadas"].update_one(
                {"chamadoId": item["chamadoId"]},
                {"$set": {
                    "mensagem_limpa": mensagem_limpa,
                    "descricao_dataset": descricao_limpa
                }},
                upsert=True
            )
            
            chamados.append({
                "chamadoId": item["chamadoId"],
                "descricao": descricao_limpa
            })
            
        except Exception as e:
            logger.error(f"Erro processando item {item.get('chamadoId')}: {str(e)}")
            continue
    
    return chamados

def obter_previsoes(chamados: list):
    """Obtém previsões de emoção para os chamados processados"""
    try:
        response = requests.post(
            "http://localhost:8080/analisar",
            json={"chamados": chamados},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("chamados", [])
    except Exception as e:
        logger.error(f"Erro ao obter previsões: {str(e)}")
        # Retorna os chamados sem análise em caso de erro
        return [{
            "chamadoId": c["chamadoId"],
            "descricao": c["descricao"],
            "emocao": "erro_na_analise"
        } for c in chamados]