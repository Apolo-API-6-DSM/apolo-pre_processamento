import re
from typing import Optional
from modules.shared.logger import logger

def limpar_mensagem(mensagem: Optional[str]) -> str:
    """Limpa mensagens do Jira removendo padrões indesejados"""
    if not mensagem:
        return ""
    
    try:
        # Padrões específicos para comentários (datas no início)
        if re.match(r'^\d{1,2}/\w{3}/\d{2}', mensagem):
            mensagem = re.sub(r'^\d{1,2}/\w{3}/\d{2}\s+\d{1,2}:\d{2}\s*[AP]M;?', '', mensagem)
        
        # Lista de padrões a serem removidos (em ordem de prioridade)
        padroes = re.compile('|'.join([
            r'\{color:[^}]+\}',
            r'https?://\S+',
            r'\|!https?://[^|]+\!\|',
            r'\|\s*\|',
            r'\{adf\}.*?\{adf\}',
            r'<\[ #gccode#[^\]]+#!',
            r'[\r\n]+',
            r'[^\w\sÀ-ÿ.,!?@#%&*+-]',  # Remove caracteres especiais não-comuns
            r'qm:[0-9a-f-]+',  # Remove UUIDs que aparecem nos comentários
            r';\d+:[0-9a-f-]+;?'  # Remove códigos com números e UUIDs
        ]), flags=re.IGNORECASE)
        
        # Aplicar todas as substituições de uma vez
        mensagem = padroes.sub(' ', mensagem)
        
        # Normalizar espaços
        mensagem = ' '.join(mensagem.split())
        
        return mensagem.strip()
    
    except Exception as e:
        logger.error(f"Erro ao limpar mensagem: {str(e)}")
        return mensagem  # Retorna original em caso de erro
    
def processar_comentarios(comentarios: list) -> list:
    """Processa uma lista de comentários"""
    if not isinstance(comentarios, list):
        return []
    
    comentarios_limpos = []
    for comentario in comentarios:
        try:
            if not isinstance(comentario, dict):
                continue
                
            texto_limpo = limpar_mensagem(comentario.get('texto', ''))
            if texto_limpo:
                comentarios_limpos.append({
                    'origem': comentario.get('origem', ''),
                    'texto': Anonimizador().anonimizar_texto(texto_limpo),
                    'tipo': comentario.get('tipo', 'comentario'),
                    'timestamp': comentario.get('timestamp', '')
                })
        except Exception as e:
            logger.error(f"Erro ao processar comentário: {str(e)}")
            continue
    
    return comentarios_limpos