"""Script de execução diária do PodcastFlow.

Pega o arquivo de notícias mais recente de um diretório monitorado,
executa o fluxo completo e salva o áudio em um diretório servido pelo site.

Ao final, atualiza o symlink 'latest.wav' para que o site sempre aponte
para o episódio mais recente sem precisar mudar a URL.

Uso:
    python scripts/daily_run.py
    python scripts/daily_run.py --input-dir /data/noticias --audio-dir /var/www/podcast/audio
    python scripts/daily_run.py --dry-run   # valida o arquivo mas não executa o fluxo
"""

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Adiciona src ao path para execução sem instalação
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from podcastflow.configuration import config
from podcastflow.graph import graph
from podcastflow.utils.helpers import save_output

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".json", ".csv", ".txt", ".md"}
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PodcastFlow — execução diária agendada via cron"
    )
    parser.add_argument(
        "--input-dir",
        default=os.getenv("PODCAST_INPUT_DIR", "data/noticias"),
        help="Diretório monitorado onde chegam os arquivos de notícias (padrão: data/noticias)",
    )
    parser.add_argument(
        "--audio-dir",
        default=os.getenv("PODCAST_AUDIO_DIR", "outputs/audio"),
        help="Diretório onde os áudios são salvos para o site (padrão: outputs/audio)",
    )
    parser.add_argument(
        "--log-dir",
        default=os.getenv("PODCAST_LOG_DIR", "outputs/logs"),
        help="Diretório de logs (padrão: outputs/logs)",
    )
    parser.add_argument(
        "--tone",
        choices=["informal", "formal", "humorístico", "técnico"],
        default=config.tone,
    )
    parser.add_argument(
        "--duration",
        choices=["curto", "médio", "longo"],
        default=config.duration,
    )
    parser.add_argument(
        "--audience",
        choices=["geral", "técnico", "executivo"],
        default=config.audience,
    )
    parser.add_argument(
        "--hosts",
        type=int,
        choices=[1, 2],
        default=config.hosts,
    )
    parser.add_argument(
        "--voice",
        default=config.tts_voice,
        help="Voz Kokoro (padrão: pf_dora para pt-BR)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=config.tts_speed,
        help="Velocidade da fala (padrão: 1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas valida o arquivo mais recente, não executa o fluxo",
    )
    return parser.parse_args()


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configura logging para arquivo e console."""
    log_dir.mkdir(parents=True, exist_ok=True)

    # Arquivo de log rotacionado por data
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"podcastflow_{today}.log"

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=handlers,
    )

    return logging.getLogger("podcastflow.daily")


def find_latest_news_file(input_dir: Path) -> Path | None:
    """Retorna o arquivo de notícias mais recente do diretório.

    Ordena por data de modificação (mtime) — o arquivo tocado por último
    é considerado o mais recente.

    Args:
        input_dir: Diretório a monitorar.

    Returns:
        Path do arquivo mais recente ou None se não houver arquivos válidos.
    """
    if not input_dir.exists():
        return None

    candidates = [
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda f: f.stat().st_mtime)


def publish_audio(raw_audio_path: str, audio_dir: Path, date_str: str) -> tuple[Path, Path]:
    """Copia o áudio gerado para o diretório do site e atualiza o symlink latest.

    Estrutura criada:
        audio_dir/
            2026-03-03.wav    ← cópia com data
            latest.wav        ← symlink sempre apontando para o mais recente

    Args:
        raw_audio_path: Caminho do WAV gerado pelo TTS (em outputs/).
        audio_dir: Diretório de destino servido pelo site.
        date_str: Data no formato YYYY-MM-DD.

    Returns:
        Tupla (caminho_datado, caminho_latest).
    """
    audio_dir.mkdir(parents=True, exist_ok=True)

    src = Path(raw_audio_path)
    dated_dest = audio_dir / f"{date_str}.wav"
    latest_link = audio_dir / "latest.wav"

    # Copia o arquivo com nome datado
    shutil.copy2(src, dated_dest)

    # Atualiza o symlink latest (remove o antigo se existir)
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(dated_dest.name)

    return dated_dest, latest_link


def write_run_manifest(audio_dir: Path, date_str: str, result: dict) -> Path:
    """Salva um JSON mínimo de metadados ao lado dos áudios para rastreabilidade.

    Args:
        audio_dir: Diretório de áudio.
        date_str: Data da execução.
        result: Estado final do grafo.

    Returns:
        Caminho do arquivo de manifesto.
    """
    manifest_path = audio_dir / f"{date_str}_manifest.json"
    manifest = {
        "date": date_str,
        "topic": result.get("topic"),
        "audio_file": f"{date_str}.wav",
        "input_file": result.get("metadata", {}).get("input_file"),
        "article_count": result.get("metadata", {}).get("article_count"),
        "audio_duration_seconds": result.get("metadata", {}).get("audio_duration_seconds"),
        "tts_voice": result.get("metadata", {}).get("tts_voice"),
        "review_iterations": result.get("review_iterations"),
        "generated_at": datetime.now().isoformat(),
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest_path


def main() -> int:
    """Executa o fluxo diário.

    Returns:
        Código de saída: 0=sucesso, 1=sem arquivo, 2=erro de execução.
    """
    args = parse_args()

    input_dir = Path(args.input_dir)
    audio_dir = Path(args.audio_dir)
    log_dir = Path(args.log_dir)

    logger = setup_logging(log_dir)

    date_str = datetime.now().strftime("%Y-%m-%d")
    logger.info("=" * 60)
    logger.info("PodcastFlow — execução diária %s", date_str)
    logger.info("input_dir=%s | audio_dir=%s", input_dir, audio_dir)

    # 1. Encontra o arquivo mais recente
    news_file = find_latest_news_file(input_dir)

    if news_file is None:
        logger.error("Nenhum arquivo de notícias encontrado em: %s", input_dir)
        logger.error("Extensões suportadas: %s", ", ".join(SUPPORTED_EXTENSIONS))
        return 1

    logger.info("Arquivo selecionado: %s (modificado em %s)",
                news_file.name,
                datetime.fromtimestamp(news_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

    if args.dry_run:
        logger.info("--dry-run ativo: validação OK, fluxo não executado.")
        return 0

    # 2. Monta o estado inicial
    run_config = {
        "tone": args.tone,
        "duration": args.duration,
        "audience": args.audience,
        "hosts": args.hosts,
        "language": config.language,
        "tts_voice": args.voice,
        "tts_speed": args.speed,
        "output_dir": str(log_dir / "tmp"),  # áudio temporário antes de publicar
    }

    initial_state = {
        "input_file": str(news_file),
        "topic": "",
        "raw_articles": [],
        "analysis": "",
        "script": "",
        "review_feedback": "",
        "review_approved": False,
        "review_iterations": 0,
        "audio_path": "",
        "social_posts": {},
        "metadata": {},
        "config": run_config,
    }

    # 3. Executa o grafo
    try:
        logger.info("Iniciando grafo LangGraph...")
        result = graph.invoke(initial_state)
    except Exception as exc:
        logger.exception("Erro fatal durante a execução do grafo: %s", exc)
        return 2

    # 4. Publica o áudio no diretório do site
    raw_audio = result.get("audio_path", "")
    if not raw_audio or not Path(raw_audio).exists():
        logger.error("Áudio não foi gerado pelo TTS. Abortando publicação.")
        return 2

    dated_path, latest_path = publish_audio(raw_audio, audio_dir, date_str)
    logger.info("Áudio publicado:")
    logger.info("  datado:  %s", dated_path)
    logger.info("  latest:  %s -> %s", latest_path, dated_path.name)

    # 5. Salva manifesto de rastreabilidade
    manifest_path = write_run_manifest(audio_dir, date_str, result)
    logger.info("Manifesto salvo: %s", manifest_path)

    # 6. Resumo final
    meta = result.get("metadata", {})
    logger.info("-" * 60)
    logger.info("CONCLUÍDO com sucesso")
    logger.info("  Tema:           %s", result.get("topic"))
    logger.info("  Artigos lidos:  %d", meta.get("article_count", 0))
    logger.info("  Duração áudio:  %.1fs", meta.get("audio_duration_seconds", 0))
    logger.info("  Tempo síntese:  %.1fs", meta.get("synthesis_time_seconds", 0))
    logger.info("  Iterações rev.: %d", result.get("review_iterations", 0))
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
