import re
from typing import Optional
from modules.shared.logger import logger

# Padrões pré-compilados para performance
REJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r'^<\[ ',
    r'postman\s+inc',
    r'avoid\s+suspension',
    r'^[\W_]+$',
    r'^[0-9]+$',
    r'[\U0001F600-\U0001F64F]'
]]

CLEANING_PATTERNS = [
    (re.compile(r'\{color[^}]*\}', re.IGNORECASE), ''),
    (re.compile(r'#gccode#\d+:\d+:\d+:[A-Za-z]+:\d+#', re.IGNORECASE), ''),
    (re.compile(r'<\[ #gccode#[^\]]+#!', re.IGNORECASE), ''),
    (re.compile(r'\{adf\}.*?\{adf\}', re.IGNORECASE|re.DOTALL), ''),
    (re.compile(r'[\U0001F600-\U0001F64F]', re.IGNORECASE), ''),
    (re.compile(r'[^\w\sÀ-ÿ.,!?@#%&*+-]', re.IGNORECASE), ''),
    (re.compile(r'^[^a-zA-Z0-9]+'), ''),
    (re.compile(r'[._]{2,}'), '.'),
    (re.compile(r'^\d+\s*'), ''),
    (re.compile(r'^\[\d+-'), ''),
    (re.compile(r'h\d+\.\s*\w+', re.IGNORECASE), ''),
    (re.compile(r'\*\s*\d+\s*anexos?\s*\*', re.IGNORECASE), ''),
    (re.compile(r'\[[^\]]+\.(pdf|jpe?g|png|docx?|xlsx?)\]', re.IGNORECASE), ''),
    (re.compile(r'(\s*\[){2,}'), ' '),
    (re.compile(r'(\s*\]){2,}'), ' '),
    (re.compile(r'[\]\},]+'), ''),
    (re.compile(r'^\W+'), ''),
    (re.compile(r'\s+'), ' '),
    (re.compile(r'\bcolou?r(s|ed|ing)?\b', re.IGNORECASE), '')  # Remove "color", "colour", "colors", etc.
]

def limpar_descricao(descricao: Optional[str]) -> str:
    """Limpa a descrição do dataset com regras rigorosas de sanitização"""
    if not isinstance(descricao, str):
        return ''
    
    descricao = descricao.strip()
    if not descricao or len(descricao) > 1000:
        return ''
    
    try:
        # Verificação de padrões de rejeição
        for pattern in REJECTION_PATTERNS:
            if pattern.search(descricao):
                return ''

        # Aplicação dos padrões de limpeza
        for pattern, replacement in CLEANING_PATTERNS:
            descricao = pattern.sub(replacement, descricao)

        # Validação final
        descricao = ' '.join(descricao.split()).strip()
        if len(descricao) < 3 or not any(c.isalpha() for c in descricao):
            return ''
            
        return descricao
    
    except Exception as e:
        logger.error(f"Erro ao limpar descrição: {str(e)}")
        return ''