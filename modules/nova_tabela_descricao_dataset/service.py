import re
from typing import Optional
from modules.shared.logger import logger

TAREFA_PATTERN = re.compile(r'Tarefa:\s*(.*?)(?=\n\w+:|$)', re.IGNORECASE)

PADROES_INVALIDOS = [
    r'^\s*$',  # Strings vazias ou só espaços
    r'^[0-9\W_]+$',  # Só números/caracteres especiais
    r'^(ok|confirmo|concordo|nada|nenhum)\s*[.!]?$'  # Respostas curtas sem valor
]

def extrair_descricao(mensagem: Optional[str]) -> str:
    """Extrai a descrição formatada para o dataset"""
    if not mensagem:
        return ""
    
    try:
        # Remove quebras de linha e espaços excessivos
        mensagem = ' '.join(mensagem.split())
        
        
        # 1. Tenta extrair conteúdo após "Tarefa:"
        tarefa_match = TAREFA_PATTERN.search(mensagem)
        if tarefa_match:
            return tarefa_match.group(1).strip()
        
        # 2. Verifica padrões de início
        padroes_inicio = [
            r'^(Bom dia|Boa tarde|Gentileza|Identificado|Olá|Ola|Prezados|Solicito|Prezado|Gostaria)'
        ]
        
        for padrao in PADROES_INVALIDOS:
            if re.fullmatch(padrao, mensagem, re.IGNORECASE):
                return ""
                
        # 3. Se não encontrar padrões, retorna os primeiros 200 caracteres
        return mensagem[:200].strip() + "..." if len(mensagem) > 200 else mensagem.strip()
        
    except Exception as e:
        logger.error(f"Erro ao extrair descrição: {str(e)}")
        return mensagem[:200].strip() if mensagem else ""