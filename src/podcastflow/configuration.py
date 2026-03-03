"""Configurações do agente PodcastFlow via Pydantic Settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PodcastConfig(BaseSettings):
    """Configurações carregadas do ambiente (.env) e/ou passadas em runtime.

    Attributes:
        google_api_key: Chave da API do Google Gemini.
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR).
        llm_model: Modelo Gemini a usar.
        llm_temperature_creative: Temperature para geração criativa (roteiro/posts).
        llm_temperature_analytic: Temperature para análise/revisão.
        tone: Tom do podcast.
        duration: Duração alvo do episódio.
        audience: Público-alvo.
        hosts: Número de apresentadores (1=monólogo, 2=diálogo).
        language: Idioma do roteiro.
        max_review_iterations: Máximo de ciclos de revisão antes de forçar aprovação.
        tts_voice: Voz Kokoro a usar para narração.
        tts_speed: Velocidade de fala (1.0 = normal).
        output_dir: Diretório para salvar os outputs.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # LLM
    llm_model: str = "gemini-2.0-flash"
    llm_temperature_creative: float = 0.7
    llm_temperature_analytic: float = 0.2

    # Parâmetros do podcast
    tone: Literal["informal", "formal", "humorístico", "técnico"] = "informal"
    duration: Literal["curto", "médio", "longo"] = "médio"
    audience: Literal["geral", "técnico", "executivo"] = "geral"
    hosts: Literal[1, 2] = 2
    language: Literal["pt-BR", "en-US", "es"] = "pt-BR"

    # Fluxo
    max_review_iterations: int = 2

    # TTS — Kokoro
    # Vozes disponíveis: af_heart, af_bella, af_nicole (en-US feminino)
    #                    am_adam, am_michael (en-US masculino)
    #                    bf_emma, bf_isabella (en-GB feminino)
    #                    bm_george, bm_lewis (en-GB masculino)
    #                    ef_dora (es), ff_siwis (fr), hf_alpha, hf_beta (hi)
    #                    if_sara (it), jf_alpha (ja), pf_dora (pt-BR feminino)
    #                    zf_xiaobei (zh)
    tts_voice: str = "pf_dora"  # pt-BR feminino nativo
    tts_speed: float = 1.0
    tts_lang: str = "p"  # prefixo de idioma Kokoro: 'p' = pt-BR

    # Output
    output_dir: str = "outputs"


# Instância global para uso nos nós
config = PodcastConfig()
