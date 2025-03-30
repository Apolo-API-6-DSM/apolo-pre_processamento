import re
from typing import Optional
from modules.shared.logger import logger

def limpar_descricao(descricao: Optional[str]) -> str:
    """Limpa a descrição do dataset com regras rigorosas de sanitização"""
    if not isinstance(descricao, str):
        return ''
    
    descricao = descricao.strip()
    if not descricao:
        return ''
    
    try:
        # 1. Verificação rigorosa para mensagens do Postman (case insensitive)
        postman_pattern = re.compile(
            r'take\s+\d+\s+min\s+today\s+to\s+see\s+your\s+monitors', 
            re.IGNORECASE
        )
        if postman_pattern.search(descricao):
            return ''

        # 2. Verificação para outros padrões de rejeição imediata
        rejection_patterns = [
            r'^<\[ ',  # Padrão técnico no início
            r'postman\s+inc',  # Mensagens do Postman
            r'avoid\s+suspension\s+of\s+your\s+postman\s+account'
        ]
        
        for pattern in rejection_patterns:
            if re.search(pattern, descricao, re.IGNORECASE):
                return ''

        # 3. Lista hierárquica de padrões de limpeza
        cleaning_patterns = [
            # Remoção de padrões complexos primeiro
            (r'\{color[^}]*\}', ''),  # {color...}
            (r'#gccode#\d+:\d+:\d+:[A-Za-z]+:\d+#', ''),  # #gccode#3:40748:374288:S:1201#
            (r'<\[ #gccode#[^\]]+#!', ''),  # <[ #gccode#...#!
            (r'\{adf\}.*?\{adf\}', '', re.DOTALL),  # {adf}...{adf}
            
            # Padrões de formatação
            (r'^\d+\s*', ''),  # Números no início
            (r'^\[\d+-', ''),  # [número-
            (r'h\d+\.\s*\w+', ''),  # h1., h2., etc
            
            # Padrões de anexos
            (r'\*\s*\d+\s*anexos?\s*\*', ''),  # *2 anexos*
            (r'\[[^\]]+\.(pdf|jpe?g|png|docx?|xlsx?)\]', '', re.IGNORECASE),  # [ARQUIVO.pdf]
            
            # Limpeza de caracteres especiais
            (r'(\s*\[){2,}', ' '),  # [[[
            (r'(\s*\]){2,}', ' '),  # ]]]
            (r'[\]\},]+', ''),  # Caracteres residuais
            (r'^\W+', ''),  # Caracteres não-alfanuméricos no início
            (r'\s+', ' ')  # Espaços múltiplos
        ]

        # 4. Aplicação dos padrões de limpeza
        for pattern in cleaning_patterns:
            if len(pattern) == 2:
                descricao = re.sub(pattern[0], pattern[1], descricao, flags=re.IGNORECASE)
            else:
                descricao = re.sub(pattern[0], pattern[1], descricao, flags=pattern[2])

        # 5. Validação final do resultado
        descricao = descricao.strip()
        if not descricao or len(descricao) < 3 or not any(c.isalnum() for c in descricao):
            return ''
            
        return descricao
    
    except Exception as e:
        logger.error(f"Erro ao limpar descrição: {str(e)}")
        return ''