import re
from typing import Optional
from modules.shared.logger import logger

def extrair_descricao(mensagem: Optional[str]) -> str:
    """Extrai a descrição formatada para o dataset"""
    if not mensagem:
        return ""
    
    try:
        # Remove quebras de linha e espaços excessivos
        mensagem = ' '.join(mensagem.split())
        
        # 1. Tenta extrair conteúdo após "Tarefa:"
        tarefa_match = re.search(r'Tarefa:\s*(.*?)(?=\n|$)', mensagem, re.IGNORECASE)
        if tarefa_match:
            return tarefa_match.group(1).strip()
        
        # 2. Verifica padrões de início
        padroes_inicio = [
            r'^(Bom dia|Boa tarde|Gentileza|Identificado|Olá|Ola|Prezados|Solicito|Prezado|Gostaria)'
        ]
        
        for padrao in padroes_inicio:
            match = re.search(padrao, mensagem, re.IGNORECASE)
            if match:
                return mensagem.strip()
                
        # 3. Se não encontrar padrões, retorna os primeiros 200 caracteres
        return mensagem[:200].strip() + "..." if len(mensagem) > 200 else mensagem.strip()
        
    except Exception as e:
        logger.error(f"Erro ao extrair descrição: {str(e)}")
        return mensagem[:200].strip() if mensagem else ""