from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from modules.shared.database import get_db
from modules.shared.logger import logger
from modules.tratamento_mensagem.service import limpar_mensagem
from modules.nova_tabela_descricao_dataset.service import extrair_descricao
from modules.tratamento_descricao_dataset.service import limpar_descricao
from modules.anonimo.service import Anonimizador
import requests
from datetime import datetime

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
            
            # Processa a mensagem principal
            mensagem_limpa = limpar_mensagem(item.get("mensagem", ""))
            descricao = extrair_descricao(mensagem_limpa)
            descricao_limpa = limpar_descricao(descricao) if descricao else ""
            
            # Processa os comentários se existirem
            comentarios_processados = []
            if 'comentarios' in item and isinstance(item['comentarios'], list):
                for comentario in item['comentarios']:
                    try:
                        texto_limpo = limpar_mensagem(comentario.get('texto', ''))
                        if texto_limpo:
                            comentarios_processados.append({
                                'origem': comentario.get('origem', ''),
                                'texto': texto_limpo,
                                'tipo': comentario.get('tipo', 'comentario'),
                                'timestamp': comentario.get('timestamp', '')
                            })
                    except Exception as e:
                        logger.error(f"Erro ao processar comentário do chamado {chamado_id}: {str(e)}")
                        continue
            
            # Anonimiza os textos
            if descricao_limpa:
                descricao_limpa = Anonimizador().anonimizar_texto(descricao_limpa)
            
            for comentario in comentarios_processados:
                comentario['texto'] = Anonimizador().anonimizar_texto(comentario['texto'])
            
            # Salva no MongoDB
            db["interacoes_processadas"].update_one(
                {"chamadoId": chamado_id},
                {"$set": {
                    "mensagem_limpa": mensagem_limpa,
                    "descricao_dataset": descricao_limpa,
                    "comentarios_processados": comentarios_processados,
                    "total_comentarios": len(comentarios_processados)
                }},
                upsert=True
            )
            
            logger.info(f"ChamadoId {chamado_id} processado e salvo no banco de dados.")
            
            # Prepara para enviar para análise
            texto_completo = descricao_limpa + " " + " ".join([c['texto'] for c in comentarios_processados])
            chamados.append({
                "chamadoId": chamado_id,
                "descricao": texto_completo.strip(),
                "tem_comentarios": len(comentarios_processados) > 0
            })
            
            if len(chamados) >= LOTE_TAMANHO:
                enviar_para_previsao(chamados)
                chamados.clear()
            
        except Exception as e:
            logger.error(f"Erro processando item {item.get('chamadoId')}: {str(e)}")
            continue

    if chamados:
        enviar_para_previsao(chamados)

def processar_apenas_anonimizacao(textos: list):
    """Processa apenas a anonimização para o formato alternativo"""
    db = get_db()
    resultados = []
    
    for texto in textos:
        try:
            texto_anonimizado = Anonimizador().anonimizar_texto(str(texto))
            resultados.append(texto_anonimizado)
            
            # Opcional: salvar no MongoDB
            db["textos_anonimizados"].insert_one({
                "texto_original": texto,
                "texto_anonimizado": texto_anonimizado,
                "data_processamento": datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Erro ao anonimizar texto: {str(e)}")
            resultados.append(None)
    
    return resultados

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
def processar_apenas_anonimizacao(ids: list):
    """Processa apenas a anonimização para o formato alternativo, buscando do MongoDB"""
    db = get_db()
    resultados = []
    
    # Busca as interações alternativas no MongoDB
    items = list(db["interacoes_alternativas"].find({"chamadoId": {"$in": ids}}))
    
    if not items:
        logger.warning("Nenhuma interação alternativa encontrada para os IDs fornecidos")
        return resultados
    
    for item in items:
        try:
            chamado_id = item.get('chamadoId')
            descricao = item.get('descricao', '')
            
            # Verifica se já foi processado
            processado = db["interacoes_alternativas_processadas"].find_one({"chamadoId": chamado_id})
            if processado:
                logger.info(f"Chamado {chamado_id} já processado. Pulando...")
                continue
                
            # Apenas anonimiza a descrição
            descricao_processada = Anonimizador().anonimizar_texto(str(descricao))
            
            # Salva no MongoDB
            db["interacoes_alternativas_processadas"].update_one(
                {"chamadoId": chamado_id},
                {"$set": {
                    "descricao_original": descricao,
                    "descricao_processada": descricao_processada,
                    "data_processamento": datetime.now()
                }},
                upsert=True
            )
            
            resultados.append({
                "chamadoId": chamado_id,
                "descricao_processada": descricao_processada
            })
            
        except Exception as e:
            logger.error(f"Erro ao processar item {chamado_id}: {str(e)}")
            continue
    
    return resultados

@router.post("/process-alternative")
async def process_alternative(request: Request, background_tasks: BackgroundTasks):
    """Endpoint específico para processamento alternativo"""
    try:
        data = await request.json()
        ids = data.get('ids', [])
        
        if not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="Formato inválido. Esperado {'ids': [...]}")
        
        if not ids:
            logger.info("Nenhum ID recebido para processamento alternativo")
            return {"status": "success", "message": "Nenhum ID para processar"}
        
        logger.info(f"Iniciando processamento alternativo para {len(ids)} chamados")
        background_tasks.add_task(processar_chamados_alternativos, ids)
        
        return {
            "status": "success",
            "message": "Processamento alternativo iniciado",
            "count": len(ids)
        }
        
    except Exception as e:
        logger.error(f"Erro no endpoint /process-alternative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def processar_chamados_alternativos(ids: list):
    """Processa chamados alternativos (apenas anonimização da descrição)"""
    db = get_db()
    processados = []
    
    try:
        chamados = list(db["interacoes_alternativas"].find(
            {"chamadoId": {"$in": ids}},
            {"chamadoId": 1, "descricao": 1}
        ))
        
        if not chamados:
            logger.warning(f"Nenhum chamado encontrado para os IDs: {ids}")
            return
            
        logger.info(f"Encontrados {len(chamados)} chamados para processar")
        
        for chamado in chamados:
            try:
                chamado_id = chamado["chamadoId"]
                descricao = chamado.get("descricao", "")
                
                if db["interacoes_alternativas_processadas"].find_one({"chamadoId": chamado_id}):
                    logger.info(f"Chamado {chamado_id} já processado. Pulando...")
                    continue
                
                descricao_processada = Anonimizador().anonimizar_texto(descricao)
                
                db["interacoes_alternativas_processadas"].insert_one({
                    "chamadoId": chamado_id,
                    "descricao_original": descricao,
                    "descricao_processada": descricao_processada,
                    "data_processamento": datetime.now(),
                    "origem": "Alternativo"
                })
                
                # Envia ambos os campos para manter compatibilidade com a IA
                processados.append({
                    "chamadoId": chamado_id,
                    "descricao": descricao_processada,  # Campo que a IA espera
                    "descricao_processada": descricao_processada  # Nosso campo adicional
                })

                # Verifica se atingiu o tamanho do lote
                if len(processados) >= LOTE_TAMANHO:
                    logger.info(f"Enviando lote de {LOTE_TAMANHO} chamados alternativos para análise")
                    enviar_para_previsao(processados)
                    processados.clear()
                
            except Exception as e:
                logger.error(f"Erro processando chamado {chamado_id}: {str(e)}")
                continue
        
        if processados:
            logger.info(f"Enviando último lote com {len(processados)} chamados alternativos")
            enviar_para_previsao(processados)
            
    except Exception as e:
        logger.error(f"Erro no processamento alternativo: {str(e)}")
        raise