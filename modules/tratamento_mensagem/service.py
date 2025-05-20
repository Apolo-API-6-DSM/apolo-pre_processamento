import re
from typing import Optional
from modules.shared.logger import logger

def limpar_mensagem(mensagem: Optional[str]) -> str:
    """Limpa mensagens do Jira removendo padrões indesejados"""
    if not mensagem:
        return ""
    
    try:
        # Lista de padrões a serem removidos (em ordem de prioridade)
        padroes = re.compile('|'.join([
            r'\{color:[^}]+\}',
            r'https?://\S+',
            r'\|!https?://[^|]+\!\|',
            r'\|\s*\|',
            r'\{adf\}.*?\{adf\}',
            r'<\[ #gccode#[^\]]+#!',
            r'[\r\n]+',
            r'[^\w\sÀ-ÿ.,!?@#%&*+-]'  # Novo: remove caracteres especiais não-comuns
        ]), flags=re.IGNORECASE)
        
        # Aplicar todas as substituições de uma vez
        mensagem = padroes.sub(' ', mensagem)
        
        # Normalizar espaços
        mensagem = ' '.join(mensagem.split())
        
        return mensagem.strip()
    
    except Exception as e:
        logger.error(f"Erro ao limpar mensagem: {str(e)}")
        return mensagem  # Retorna original em caso de erro