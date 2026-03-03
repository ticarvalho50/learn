#!/usr/bin/env bash
# =============================================================================
# cron_wrapper.sh — Wrapper do PodcastFlow para execução via cron
#
# Responsabilidades:
#   1. Ativa o virtualenv correto
#   2. Carrega o .env com as API keys
#   3. Executa daily_run.py
#   4. Envia um log de status simples (sucesso ou falha)
#
# Instalação do cron job (edite com: crontab -e):
#   0 8 * * * /caminho/para/podcastflow/scripts/cron_wrapper.sh
#
# Variáveis de ambiente obrigatórias (.env ou exportadas no shell):
#   GOOGLE_API_KEY       — API key do Google Gemini
#   PODCAST_INPUT_DIR    — diretório com os arquivos de notícias
#   PODCAST_AUDIO_DIR    — diretório de saída de áudio para o site
#   PODCAST_LOG_DIR      — diretório de logs (padrão: outputs/logs)
#   PODCAST_VENV_PATH    — caminho do virtualenv (padrão: .venv)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuração — edite conforme seu ambiente
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Carrega variáveis do .env se existir
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    set -a
    source "$ENV_FILE"
    set +a
fi

# Caminho do virtualenv (sobrescrito por PODCAST_VENV_PATH se definido)
VENV_PATH="${PODCAST_VENV_PATH:-${PROJECT_ROOT}/.venv}"

# Diretórios configuráveis via env
INPUT_DIR="${PODCAST_INPUT_DIR:-${PROJECT_ROOT}/data/noticias}"
AUDIO_DIR="${PODCAST_AUDIO_DIR:-${PROJECT_ROOT}/outputs/audio}"
LOG_DIR="${PODCAST_LOG_DIR:-${PROJECT_ROOT}/outputs/logs}"

# Parâmetros do podcast (sobrescrevem os defaults do código)
TONE="${PODCAST_TONE:-informal}"
DURATION="${PODCAST_DURATION:-médio}"
HOSTS="${PODCAST_HOSTS:-2}"
VOICE="${PODCAST_VOICE:-pf_dora}"
SPEED="${PODCAST_SPEED:-1.0}"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

mkdir -p "$LOG_DIR"

TODAY=$(date +%Y-%m-%d)
LOG_FILE="${LOG_DIR}/cron_${TODAY}.log"
LOCK_FILE="/tmp/podcastflow_daily.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Previne execução paralela (ex: se o job anterior ainda está rodando)
if [[ -f "$LOCK_FILE" ]]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE") ))
    if [[ $LOCK_AGE -lt 7200 ]]; then  # 2 horas
        log "AVISO: lock file encontrado (${LOCK_AGE}s atrás). Execução anterior ainda em progresso? Abortando."
        exit 1
    else
        log "Lock file antigo (${LOCK_AGE}s). Removendo e continuando."
        rm -f "$LOCK_FILE"
    fi
fi

touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# ---------------------------------------------------------------------------
# Ativa o virtualenv
# ---------------------------------------------------------------------------

if [[ ! -f "${VENV_PATH}/bin/activate" ]]; then
    log "ERRO: virtualenv não encontrado em ${VENV_PATH}"
    log "Crie com: python -m venv ${VENV_PATH} && ${VENV_PATH}/bin/pip install -e '${PROJECT_ROOT}[dev]'"
    exit 2
fi

# shellcheck source=/dev/null
source "${VENV_PATH}/bin/activate"
log "Virtualenv ativado: ${VENV_PATH}"

# ---------------------------------------------------------------------------
# Executa o fluxo diário
# ---------------------------------------------------------------------------

log "Iniciando PodcastFlow daily_run.py"
log "INPUT_DIR=${INPUT_DIR} | AUDIO_DIR=${AUDIO_DIR}"

PYTHON="${VENV_PATH}/bin/python"

EXIT_CODE=0
"$PYTHON" "${SCRIPT_DIR}/daily_run.py" \
    --input-dir  "$INPUT_DIR"  \
    --audio-dir  "$AUDIO_DIR"  \
    --log-dir    "$LOG_DIR"    \
    --tone       "$TONE"       \
    --duration   "$DURATION"   \
    --hosts      "$HOSTS"      \
    --voice      "$VOICE"      \
    --speed      "$SPEED"      \
    >> "$LOG_FILE" 2>&1 || EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Status final
# ---------------------------------------------------------------------------

if [[ $EXIT_CODE -eq 0 ]]; then
    log "SUCESSO — podcast do dia gerado em ${AUDIO_DIR}/${TODAY}.wav"
elif [[ $EXIT_CODE -eq 1 ]]; then
    log "AVISO — nenhum arquivo de notícias encontrado em ${INPUT_DIR}"
else
    log "ERRO — falha durante a execução (exit code ${EXIT_CODE}). Veja o log: ${LOG_FILE}"
fi

exit "$EXIT_CODE"
