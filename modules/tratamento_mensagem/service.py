import re
from typing import Optional
from modules.shared.logger import logger

def limpar_mensagem(mensagem: Optional[str]) -> str:
    """Limpa mensagens do Jira removendo padrões indesejados"""
    if not mensagem:
        return ""
    
    try:
        # Lista de padrões a serem removidos (em ordem de prioridade)
        padroes = [
            r'\{color:[^}]+\}',          # {color:#5b5b5b}
            r'https?://\S+',              # URLs
            r'\|!https?://[^|]+\!\|',     # |!http...!|
            r'\|\s*\|',                   # | |
            r'\{adf\}.*?\{adf\}',         # {adf}...{adf}
            r'<\[ #gccode#[^\]]+#!',      # <[ #gccode#...#!
            r'[\r\n]+',                   # Quebras de linha
            r'\s{2,}'                     # Múltiplos espaços
        ]
        
        for padrao in padroes:
            mensagem = re.sub(padrao, ' ', mensagem)
            
        return mensagem.strip()
    
    except Exception as e:
        logger.error(f"Erro ao limpar mensagem: {str(e)}")
        return mensagem  # Retorna original em caso de erro