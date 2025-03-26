import re
from typing import Optional, List
import spacy
from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from modules.shared.logger import logger
from .patterns import PADROES_PERSONALIZADOS

class Anonimizador:
    _instance = None
    _ESPACOS_REGEX = re.compile(r'\s+')
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Anonimizador, cls).__new__(cls)
            cls._instance._inicializado = False
        return cls._instance
    
    def __init__(self):
        if not self._inicializado:
            try:
                self.nlp = self._carregar_modelo_spacy()
                self.analyzer, self.anonymizer = self._configurar_presidio()
                self._inicializado = True
            except Exception as e:
                logger.critical(f"Falha ao inicializar Anonimizador: {str(e)}")
                raise

    def _carregar_modelo_spacy(self):
        """Carrega o modelo spaCy uma única vez"""
        try:
            nlp = spacy.load("pt_core_news_lg", disable=["parser", "tagger"])
            logger.info("Modelo spaCy carregado com sucesso")
            return nlp
        except OSError as e:
            logger.error("Modelo spaCy não encontrado. Execute: python -m spacy download pt_core_news_lg")
            raise RuntimeError("Modelo de linguagem não disponível") from e

    def _configurar_presidio(self):
        """Configura o Presidio para usar o modelo spaCy já carregado"""
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}],
        }

        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["pt"],
            default_score_threshold=0.7
        )

        # Adiciona padrões customizados com verificação
        for padrao in PADROES_PERSONALIZADOS:
            try:
                recognizer = PatternRecognizer(
                    supported_entity=padrao["entidade"],
                    patterns=padrao["padroes"],
                    supported_language="pt",
                    context=padrao.get("contexto", [])
                )
                analyzer.registry.add_recognizer(recognizer)
            except Exception as e:
                logger.warning(f"Erro ao adicionar padrão {padrao.get('entidade')}: {str(e)}")

        return analyzer, AnonymizerEngine()

    def _identificar_nomes_manualmente(self, texto: str) -> List[str]:
        """Identifica nomes com verificação mais segura"""
        PALAVRAS_IGNORAR = {
            "solicito", "Solicito", "Peço", "peço", "Pedido", "Atenciosamente", "att", "contrato", "termo", "formulário", 
            "atenciosamente", "exclusão", "sistema"
        }
        
        try:
            if not texto:
                return []
                
            doc = self.nlp(texto)
            return [
                ent.text 
                for ent in doc.ents 
                if (ent.label_ in ("PER", "PERSON") and
                    len(ent.text.split()) > 1 and
                    ent.text.lower() not in PALAVRAS_IGNORAR and
                    not any(palavra.lower() in PALAVRAS_IGNORAR
                        for palavra in ent.text.split()))
            ]
        except Exception as e:
            logger.warning(f"Erro ao identificar nomes: {str(e)}")
            return []

    def anonimizar_texto(self, texto: Optional[str]) -> str:
        """Versão melhorada do método de anonimização"""
        if not texto or not isinstance(texto, str):
            return ""

        try:
            # Lista de palavras para preservar (não anonimizar)
            PALAVRAS_PRESERVAR = {
                "Solicito", "solicito", "Peço", "peço", "Olá", "Contrato",
                "Atenciosamente", "atenciosamente", "Termo", "Formulário"
            }
            contextos = ["cadastro", "dados", "colaborador", "documento", "cliente", "usuário", "funcionário"]
            
            # Primeira passada com Presidio
            resultados = self.analyzer.analyze(
                text=texto,
                language="pt",
                context=contextos,
                score_threshold=0.8  # Threshold mais baixo para capturar mais entidades
            )

            # Filtra resultados para remover entidades que são palavras a preservar
            resultados_filtrados = [
                r for r in resultados 
                if texto[r.start:r.end] not in PALAVRAS_PRESERVAR
            ]
            
            texto_anonimizado = self.anonymizer.anonymize(
                text=texto, 
                analyzer_results=resultados_filtrados
            ).text

            # 3. Identificação manual de nomes (com palavras preservadas)
            nomes = set(
                nome for nome in self._identificar_nomes_manualmente(texto_anonimizado)
                if nome not in PALAVRAS_PRESERVAR
            )

            for nome in nomes:
                texto_anonimizado = re.sub(
                    r'\b' + re.escape(nome) + r'\b',
                    "<PERSON>",
                    texto_anonimizado
                )

            # 4. Pós-processamento para corrigir substituições indesejadas
            substituicoes = {
                "<LOCATION> Olá": "Olá",
                "<LOCATION> a": "a",
                "<LOCATION> \\": "\\",
                "<ORGANIZATION>": "Termo"
            }
            
            for padrao, substituicao in substituicoes.items():
                texto_anonimizado = texto_anonimizado.replace(padrao, substituicao)

            return self._ESPACOS_REGEX.sub(' ', texto_anonimizado).strip()
            
        except Exception as e:
            logger.error(f"Erro ao anonimizar texto. Texto: '{texto[:50]}...'. Erro: {str(e)}")
            return texto