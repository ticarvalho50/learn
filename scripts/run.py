"""Entrypoint CLI do PodcastFlow.

Uso:
    python scripts/run.py --file noticias.json
    python scripts/run.py --file noticias.csv --tone formal --duration longo --hosts 1
    python scripts/run.py --file noticias.txt --topic "IA em 2025" --no-tts
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Adiciona o src ao path para execução sem instalação do pacote
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from podcastflow.configuration import config
from podcastflow.graph import graph
from podcastflow.utils.helpers import save_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PodcastFlow — gera podcast e posts a partir de notícias locais"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Caminho para o arquivo de notícias (.json, .csv ou .txt)",
    )
    parser.add_argument(
        "--topic",
        default="",
        help="Tema do episódio (opcional, derivado do nome do arquivo se omitido)",
    )
    parser.add_argument(
        "--tone",
        choices=["informal", "formal", "humorístico", "técnico"],
        default=config.tone,
        help="Tom do podcast (padrão: %(default)s)",
    )
    parser.add_argument(
        "--duration",
        choices=["curto", "médio", "longo"],
        default=config.duration,
        help="Duração alvo: curto=5min, médio=15min, longo=30min (padrão: %(default)s)",
    )
    parser.add_argument(
        "--audience",
        choices=["geral", "técnico", "executivo"],
        default=config.audience,
        help="Público-alvo (padrão: %(default)s)",
    )
    parser.add_argument(
        "--hosts",
        type=int,
        choices=[1, 2],
        default=config.hosts,
        help="1=monólogo, 2=diálogo (padrão: %(default)s)",
    )
    parser.add_argument(
        "--language",
        choices=["pt-BR", "en-US", "es"],
        default=config.language,
        help="Idioma do roteiro (padrão: %(default)s)",
    )
    parser.add_argument(
        "--voice",
        default=config.tts_voice,
        help=(
            "Voz Kokoro para narração (padrão: %(default)s). "
            "Vozes pt-BR: pf_dora. "
            "Vozes en-US: af_heart, af_bella, am_adam, am_michael."
        ),
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=config.tts_speed,
        help="Velocidade de fala — 1.0=normal, 0.8=lento, 1.2=rápido (padrão: %(default)s)",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Pula a geração de áudio (útil para testar apenas o roteiro)",
    )
    parser.add_argument(
        "--output-dir",
        default=config.output_dir,
        help="Diretório de saída para áudio e JSON (padrão: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=config.log_level,
        help="Nível de log (padrão: %(default)s)",
    )
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    logger = logging.getLogger("podcastflow.run")
    logger.info("PodcastFlow iniciando...")
    logger.info("Arquivo: %s | Tom: %s | Duração: %s | Hosts: %d", args.file, args.tone, args.duration, args.hosts)

    # Configura o estado inicial
    run_config: dict = {
        "tone": args.tone,
        "duration": args.duration,
        "audience": args.audience,
        "hosts": args.hosts,
        "language": args.language,
        "tts_voice": args.voice,
        "tts_speed": args.speed,
        "output_dir": args.output_dir,
    }

    initial_state = {
        "input_file": args.file,
        "topic": args.topic,
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

    # Se --no-tts, usa um grafo sem o nó TTS
    if args.no_tts:
        from podcastflow._graph_no_tts import graph as no_tts_graph
        result = no_tts_graph.invoke(initial_state)
    else:
        result = graph.invoke(initial_state)

    # Salva output completo
    output_file = save_output(result, args.output_dir)

    # Exibe resumo
    print("\n" + "=" * 60)
    print("PODCAST GERADO COM SUCESSO")
    print("=" * 60)
    print(f"Tema:       {result.get('topic')}")
    print(f"Áudio:      {result.get('audio_path') or 'não gerado (--no-tts)'}")
    print(f"Output:     {output_file}")
    print(f"Iterações:  {result.get('review_iterations', 0)}")

    posts = result.get("social_posts", {})
    if posts:
        print("\n--- POSTS ---")
        for platform, post in posts.items():
            print(f"\n[{platform.upper()}]\n{post}")

    print("\n--- ROTEIRO (primeiras 500 chars) ---")
    script = result.get("script", "")
    print(script[:500] + ("..." if len(script) > 500 else ""))
    print("=" * 60)


if __name__ == "__main__":
    main()
