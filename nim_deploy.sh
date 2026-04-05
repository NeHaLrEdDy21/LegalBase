#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# LegalMind — NVIDIA NIM Deployment Helper
#
# TWO MODES
# ─────────
# 1. --hosted   (default when GPU VRAM < 64 GB)
#    Validates your NGC API key against the NVIDIA cloud inference endpoint.
#    No GPU required — inference runs on NVIDIA's cloud.
#    Requires: NGC_API_KEY=nvapi-xxxx (get at ngc.nvidia.com → Setup → API Keys)
#
# 2. --self-hosted
#    Pulls and runs the Gemma 4 31B NIM Docker container locally.
#    Requires: ≥64 GB GPU VRAM, Docker with NVIDIA Container Toolkit
#
# USAGE
# ─────
# export NGC_API_KEY="nvapi-xxxxxxxxxxxx"
# bash nim_deploy.sh              # auto-selects mode based on VRAM
# bash nim_deploy.sh --hosted     # force hosted mode
# bash nim_deploy.sh --self-hosted  # force self-hosted mode
#
# WINDOWS NOTE
# ─────────────
# Self-hosted mode runs Docker inside WSL2 (Ubuntu-22.04).
# Hosted mode works directly on Windows (only needs curl / Python).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
NIM_IMAGE="nvcr.io/nim/google/gemma-4-31b-it:latest"
NIM_MODEL="google/gemma-4-31b-it"
CONTAINER_NAME="legalmind-nim-gemma4-31b"
HOST_PORT=8001
NIM_CACHE_DIR="${HOME}/.cache/nim/gemma-4-31b"

HOSTED_ENDPOINT="https://integrate.api.nvidia.com/v1"
SELF_HOSTED_ENDPOINT="http://localhost:${HOST_PORT}/v1"

MIN_VRAM_MB=65536   # 64 GB

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[NIM]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}${CYAN}$*${NC}\n"; }

# ── OS / WSL2 detection ───────────────────────────────────────────────────────
IS_WINDOWS=false
IS_WSL=false

if [[ -n "${WINDIR:-}" ]] || [[ "$(uname -s)" == "MINGW"* ]] || [[ "$(uname -s)" == "CYGWIN"* ]]; then
  IS_WINDOWS=true
fi
if grep -qi microsoft /proc/version 2>/dev/null; then
  IS_WSL=true
fi

# ── Parse args ────────────────────────────────────────────────────────────────
MODE=""
for arg in "$@"; do
  case "$arg" in
    --hosted)       MODE="hosted"      ;;
    --self-hosted)  MODE="self-hosted" ;;
    *)              warn "Unknown argument: $arg" ;;
  esac
done

# ── NGC_API_KEY check ─────────────────────────────────────────────────────────
if [[ -z "${NGC_API_KEY:-}" ]]; then
  error "NGC_API_KEY is not set.\n\n  Get a free key at:  https://ngc.nvidia.com → Setup → API Keys\n  Then run:           export NGC_API_KEY=\"nvapi-...\"\n  And re-run:         bash nim_deploy.sh"
fi
info "NGC_API_KEY detected ✓"

# ── Auto-select mode if not specified ────────────────────────────────────────
if [[ -z "$MODE" ]]; then
  if command -v nvidia-smi &>/dev/null; then
    TOTAL_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | awk '{s+=$1} END{print s+0}')
  else
    TOTAL_VRAM_MB=0
  fi

  if (( TOTAL_VRAM_MB >= MIN_VRAM_MB )); then
    MODE="self-hosted"
    info "Detected ${TOTAL_VRAM_MB} MiB VRAM → self-hosted mode selected."
  else
    MODE="hosted"
    if (( TOTAL_VRAM_MB > 0 )); then
      warn "Detected only ${TOTAL_VRAM_MB} MiB VRAM (need ${MIN_VRAM_MB}+ for Gemma 4 31B)."
    fi
    info "→ Using NVIDIA cloud-hosted inference (no local GPU required)."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: hosted
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$MODE" == "hosted" ]]; then
  header "NVIDIA Cloud-Hosted NIM — Gemma 4 31B"

  info "Validating NGC API key against ${HOSTED_ENDPOINT} ..."

  HTTP_STATUS=$(curl -s -o /tmp/nim_models.json -w "%{http_code}" \
    "${HOSTED_ENDPOINT}/models" \
    -H "Authorization: Bearer ${NGC_API_KEY}")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    success "API key is valid ✓"
    MODEL_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/nim_models.json')); print(len(d.get('data', [])))" 2>/dev/null || echo "?")
    info "Available models: ${MODEL_COUNT}"
  else
    error "API key validation failed (HTTP ${HTTP_STATUS}).\n  Response: $(cat /tmp/nim_models.json)\n  Check your key at: https://ngc.nvidia.com → Setup → API Keys"
  fi

  # Quick smoke test
  info "Running smoke test against ${NIM_MODEL} ..."
  RESPONSE=$(curl -sf "${HOSTED_ENDPOINT}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${NGC_API_KEY}" \
    -d "{
      \"model\": \"${NIM_MODEL}\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Reply with OK only.\"}],
      \"max_tokens\": 8
    }")
  REPLY=$(echo "${RESPONSE}" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])" 2>/dev/null || echo "(parse error)")
  success "Smoke test passed — model replied: ${REPLY}"

  # Write .env snippet
  ENV_FILE="$(dirname "$0")/backend/.env"
  if [[ -f "$ENV_FILE" ]]; then
    # Uncomment or add the NIM lines
    if grep -q "^# NGC_API_KEY=" "$ENV_FILE"; then
      sed -i "s|^# NGC_API_KEY=.*|NGC_API_KEY=${NGC_API_KEY}|" "$ENV_FILE"
      sed -i "s|^# NIM_BASE_URL=.*|NIM_BASE_URL=${HOSTED_ENDPOINT}|" "$ENV_FILE"
      sed -i "s|^# NIM_MODEL=.*|NIM_MODEL=${NIM_MODEL}|" "$ENV_FILE"
      sed -i "s|^LLM_PROVIDER=.*|LLM_PROVIDER=nim|" "$ENV_FILE"
      success "backend/.env updated — LLM_PROVIDER=nim, NIM_BASE_URL=${HOSTED_ENDPOINT}"
    else
      warn "backend/.env exists but the NIM placeholder lines weren't found. Update manually."
    fi
  fi

  echo ""
  echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  NVIDIA Cloud NIM — Ready                             ${NC}"
  echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "  Endpoint:  ${CYAN}${HOSTED_ENDPOINT}${NC}"
  echo -e "  Model:     ${CYAN}${NIM_MODEL}${NC}"
  echo -e "  Docs:      ${CYAN}https://build.nvidia.com/google/gemma-4-31b-it${NC}"
  echo ""
  echo -e "  backend/.env should have:"
  echo -e "    ${YELLOW}LLM_PROVIDER=nim${NC}"
  echo -e "    ${YELLOW}NGC_API_KEY=${NGC_API_KEY:0:12}...${NC}"
  echo -e "    ${YELLOW}NIM_BASE_URL=${HOSTED_ENDPOINT}${NC}"
  echo ""
  echo -e "  Restart the backend to activate NIM:  uvicorn app.main:app --reload"
  echo ""
  exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: self-hosted
# ═════════════════════════════════════════════════════════════════════════════
header "NVIDIA Self-Hosted NIM — Gemma 4 31B (${NIM_IMAGE})"

# On Windows, route everything through WSL2
if $IS_WINDOWS && ! $IS_WSL; then
  info "Windows host detected — routing self-hosted commands through WSL2 (Ubuntu-22.04)."
  DISTRO="${WSL_DISTRO:-Ubuntu-22.04}"

  # Check WSL2 is available
  if ! wsl.exe -d "$DISTRO" -- echo "WSL2 OK" &>/dev/null; then
    error "WSL2 distro '$DISTRO' not found.\n  Install it with:  wsl --install Ubuntu-22.04\n  Then re-run this script."
  fi

  # Re-run this script inside WSL2
  WIN_SCRIPT="$(realpath "$0")"
  WSL_SCRIPT=$(wsl.exe -d "$DISTRO" -- wslpath -u "$(echo "$WIN_SCRIPT" | sed 's|\\|/|g')" 2>/dev/null || echo "")

  if [[ -z "$WSL_SCRIPT" ]]; then
    error "Could not translate Windows path to WSL path.\n  Run manually in WSL2: bash /path/to/nim_deploy.sh --self-hosted"
  fi

  exec wsl.exe -d "$DISTRO" -- bash -c "NGC_API_KEY='${NGC_API_KEY}' bash '${WSL_SCRIPT}' --self-hosted"
fi

# ── 1. Verify nvidia-smi ──────────────────────────────────────────────────────
if ! command -v nvidia-smi &>/dev/null; then
  error "nvidia-smi not found. Ensure NVIDIA drivers (535+) are installed.\n  Docs: https://docs.nvidia.com/cuda/cuda-installation-guide-linux/"
fi
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
TOTAL_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{s+=$1} END{print s}')
info "Detected ${GPU_COUNT} GPU(s) — total VRAM: ${TOTAL_VRAM_MB} MiB"
if (( TOTAL_VRAM_MB < MIN_VRAM_MB )); then
  warn "Gemma 4 31B requires ~64 GB VRAM (FP16). Detected ${TOTAL_VRAM_MB} MiB."
  warn "The container may fail to load the model. Consider --hosted instead."
fi

# ── 2. Install NVIDIA Container Toolkit (if missing) ─────────────────────────
if ! command -v nvidia-ctk &>/dev/null; then
  warn "nvidia-ctk not found — installing NVIDIA Container Toolkit..."
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  sudo apt-get update -qq
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo service docker restart 2>/dev/null || sudo systemctl restart docker 2>/dev/null || true
  success "NVIDIA Container Toolkit installed."
else
  success "NVIDIA Container Toolkit already installed ($(nvidia-ctk --version 2>/dev/null | head -1))."
fi

# ── 3. Docker login ───────────────────────────────────────────────────────────
info "Authenticating with nvcr.io..."
echo "${NGC_API_KEY}" | docker login nvcr.io --username '$oauthtoken' --password-stdin
success "Docker login successful."

# ── 4. Cache directory ────────────────────────────────────────────────────────
mkdir -p "${NIM_CACHE_DIR}"
success "NIM cache directory: ${NIM_CACHE_DIR}"

# ── 5. Stop existing container (if any) ──────────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  warn "Stopping existing container '${CONTAINER_NAME}'..."
  docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker rm   "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

# ── 6. Launch NIM container ───────────────────────────────────────────────────
info "Pulling & starting ${NIM_IMAGE} ..."
info "⏳ First run downloads ~60 GB of model weights — this can take 15-30 min."

docker run -d \
  --name  "${CONTAINER_NAME}" \
  --gpus  all \
  --ipc   host \
  --shm-size 16g \
  -e NGC_API_KEY="${NGC_API_KEY}" \
  -v "${NIM_CACHE_DIR}:/root/.cache/nim" \
  -p "${HOST_PORT}:8000" \
  --restart unless-stopped \
  "${NIM_IMAGE}"

success "Container '${CONTAINER_NAME}' started on port ${HOST_PORT}."

# ── 7. Wait for readiness ─────────────────────────────────────────────────────
info "Waiting for NIM server to become ready (up to 10 min)..."
MAX_WAIT=600; INTERVAL=10; elapsed=0
until curl -sf "http://localhost:${HOST_PORT}/v1/models" -o /dev/null; do
  if (( elapsed >= MAX_WAIT )); then
    error "NIM server did not respond within ${MAX_WAIT}s.\n  Check logs:  docker logs ${CONTAINER_NAME}"
  fi
  echo -n "."
  sleep ${INTERVAL}
  (( elapsed += INTERVAL ))
done
echo ""
success "NIM server is ready! 🚀"

# ── 8. Quick smoke test ───────────────────────────────────────────────────────
info "Running smoke test..."
RESPONSE=$(curl -sf "http://localhost:${HOST_PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${NIM_MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Reply with OK only.\"}],
    \"max_tokens\": 8
  }")
REPLY=$(echo "${RESPONSE}" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])" 2>/dev/null || echo "(parse error)")
success "Smoke test passed — model replied: ${REPLY}"

# ── 9. Print summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Gemma 4 31B NIM is running (self-hosted)             ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  API endpoint:   ${CYAN}${SELF_HOSTED_ENDPOINT}${NC}"
echo -e "  Model ID:       ${CYAN}${NIM_MODEL}${NC}"
echo -e "  Swagger UI:     ${CYAN}http://localhost:${HOST_PORT}/docs${NC}"
echo -e "  Container logs: docker logs -f ${CONTAINER_NAME}"
echo ""
echo -e "  Set in backend/.env:"
echo -e "    ${YELLOW}LLM_PROVIDER=nim${NC}"
echo -e "    ${YELLOW}NIM_BASE_URL=${SELF_HOSTED_ENDPOINT}${NC}"
echo ""
