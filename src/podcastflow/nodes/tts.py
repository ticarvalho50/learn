"""Nó TTS — converte o roteiro em áudio usando Kokoro ONNX.

Kokoro é um modelo TTS leve (~82M parâmetros) com qualidade de fala extremamente
natural. Suporta vozes pt-BR (pf_dora), en-US, en-GB, es, fr, ja, zh e mais.

Referência: https://github.com/thewh1teagle/kokoro-onnx
"""

import logging
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from podcastflow.configuration import config
from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)

# Marcadores de entonação/direção que devem ser removidos do texto antes do TTS
_DIRECTION_PATTERN = re.compile(
    r"\[(?:PAUSA|ANIMADO|SÉRIO|CURIOSO|REFLEXIVO|HOST1|HOST2|PAUSA CURTA|PAUSA LONGA)\]",
    re.IGNORECASE,
)

# Prefixos de apresentadores em diálogo (HOST1:, HOST2:)
_HOST_PREFIX_PATTERN = re.compile(r"^HOST\d+:\s*", re.MULTILINE | re.IGNORECASE)

# Cabeçalhos de seção markdown
_SECTION_HEADER_PATTERN = re.compile(r"^#{1,3}\s+.*$", re.MULTILINE)


def tts_narrate(state: PodcastState) -> dict:
    """Converte o roteiro aprovado em arquivo de áudio MP3/WAV via Kokoro ONNX.

    Estratégia de síntese:
    - O roteiro é dividido em sentenças para permitir síntese incremental
    - Cada sentença é convertida individualmente e concatenada
    - Pausas entre blocos são inseridas como silêncio programático

    Args:
        state: Estado atual com 'script' aprovado.

    Returns:
        Dicionário com 'audio_path' e 'metadata' atualizado.
    """
    script = state["script"]
    cfg = state.get("config", {})

    voice = cfg.get("tts_voice", config.tts_voice)
    speed = float(cfg.get("tts_speed", config.tts_speed))
    lang = cfg.get("tts_lang", config.tts_lang)
    output_dir = Path(cfg.get("output_dir", config.output_dir))

    logger.info("tts_narrate | iniciando síntese | voz=%s | velocidade=%.1f", voice, speed)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = re.sub(r"[^\w]", "_", state.get("topic", "podcast"))[:40]
    output_path = output_dir / f"{timestamp}_{topic_slug}.wav"

    kokoro = _load_kokoro(lang, voice)

    clean_script = _clean_script_for_tts(script)
    sentences = _split_into_sentences(clean_script)

    logger.info("tts_narrate | %d sentenças para sintetizar", len(sentences))

    audio_segments: list[np.ndarray] = []
    sample_rate = 24000  # Kokoro usa 24kHz

    start_time = time.time()

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            # Insere 0.5s de silêncio para parágrafos vazios
            audio_segments.append(np.zeros(int(0.5 * sample_rate), dtype=np.float32))
            continue

        try:
            samples, sr = kokoro.create(sentence, voice=voice, speed=speed, lang=lang)
            audio_segments.append(samples)

            # Pequena pausa natural entre sentenças (0.15s)
            audio_segments.append(np.zeros(int(0.15 * sr), dtype=np.float32))

        except Exception as exc:
            logger.warning("tts_narrate | erro na sentença %d: %s — pulando", i, exc)
            continue

    if not audio_segments:
        raise RuntimeError("Nenhum segmento de áudio foi gerado pelo TTS.")

    final_audio = np.concatenate(audio_segments)
    sf.write(str(output_path), final_audio, sample_rate)

    elapsed = time.time() - start_time
    duration_sec = len(final_audio) / sample_rate
    logger.info(
        "tts_narrate | áudio salvo: %s | duração=%.1fs | tempo_síntese=%.1fs",
        output_path,
        duration_sec,
        elapsed,
    )

    metadata = state.get("metadata", {})
    metadata.update(
        {
            "audio_path": str(output_path),
            "audio_duration_seconds": round(duration_sec, 1),
            "tts_voice": voice,
            "tts_speed": speed,
            "synthesis_time_seconds": round(elapsed, 1),
        }
    )

    return {
        "audio_path": str(output_path),
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_kokoro(lang: str, voice: str):
    """Carrega o modelo Kokoro ONNX.

    Faz download automático do modelo na primeira execução (~300MB).
    Em execuções seguintes, usa o cache local.

    Args:
        lang: Prefixo de idioma Kokoro (ex: 'p' para pt-BR).
        voice: Nome da voz (ex: 'pf_dora').

    Returns:
        Instância de KokoroOnnx pronta para uso.
    """
    try:
        from kokoro_onnx import Kokoro  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "kokoro-onnx não está instalado. Execute: pip install kokoro-onnx"
        ) from exc

    logger.info("tts_narrate | carregando modelo Kokoro (pode demorar na 1ª execução)...")
    kokoro = Kokoro.from_pretrained("kokoro-v1.0.onnx", "voices-v1.0.bin")
    logger.info("tts_narrate | modelo Kokoro carregado")
    return kokoro


def _clean_script_for_tts(script: str) -> str:
    """Remove marcadores de direção, prefixos de host e headers markdown.

    Mantém apenas o texto falado puro, adequado para síntese de voz.

    Args:
        script: Roteiro completo com marcadores.

    Returns:
        Texto limpo para o TTS.
    """
    text = _SECTION_HEADER_PATTERN.sub("", script)
    text = _HOST_PREFIX_PATTERN.sub("", text)
    text = _DIRECTION_PATTERN.sub(" ", text)

    # Colapsa múltiplas quebras de linha em uma única
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove traços decorativos (--- separadores)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)

    return text.strip()


def _split_into_sentences(text: str) -> list[str]:
    """Divide o texto em sentenças para síntese incremental.

    Divide nos pontos finais, exclamações, interrogações e parágrafos.
    Mantém sentenças com no mínimo 10 e máximo 300 caracteres para
    compatibilidade com o Kokoro.

    Args:
        text: Texto limpo do roteiro.

    Returns:
        Lista de sentenças.
    """
    # Primeiro divide por parágrafos
    paragraphs = text.split("\n\n")
    sentences: list[str] = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            sentences.append("")  # marcador de pausa
            continue

        # Divide por pontuação final
        parts = re.split(r"(?<=[.!?])\s+", paragraph)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Fragmenta sentenças muito longas
            if len(part) > 300:
                sub_parts = _chunk_long_sentence(part, max_len=300)
                sentences.extend(sub_parts)
            elif len(part) >= 5:
                sentences.append(part)

    return sentences


def _chunk_long_sentence(sentence: str, max_len: int = 300) -> list[str]:
    """Divide uma sentença longa em fragmentos por vírgulas ou espaços.

    Args:
        sentence: Sentença a dividir.
        max_len: Tamanho máximo de cada fragmento.

    Returns:
        Lista de fragmentos.
    """
    if len(sentence) <= max_len:
        return [sentence]

    # Tenta dividir por vírgulas
    parts = sentence.split(", ")
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = f"{current}, {part}" if current else part
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = part

    if current:
        chunks.append(current)

    return chunks if chunks else [sentence[:max_len]]
