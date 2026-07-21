#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export HWP_ANALYSIS_ROOT="${HWP_ANALYSIS_ROOT:-/home/eunbi/HWP analysis}"
export PYTHONPATH="${ROOT}:${HWP_ANALYSIS_ROOT}:${HWP_ANALYSIS_ROOT}/HWP_v2:${PYTHONPATH:-}"
cd "$ROOT"
exec streamlit run app.py --server.port "${PORT:-8502}" --server.address "${HOST:-127.0.0.1}"
