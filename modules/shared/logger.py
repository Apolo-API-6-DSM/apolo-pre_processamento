import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração básica do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formato das mensagens
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

# Handler para console
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# Handler para arquivo (opcional)
log_file = os.getenv("LOG_FILE", "app.log")
fh = RotatingFileHandler(
    log_file,
    maxBytes=1024*1024,
    backupCount=5
)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Exporta o logger para uso em outros módulos
__all__ = ['logger']