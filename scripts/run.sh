#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

FM4_BIN="${REPO_ROOT}/out/build/linux-amd64-release/fm4"
if [ ! -f "${FM4_BIN}" ]; then
  echo "Error: fm4 binary not found. Run scripts/build.sh first." >&2
  exit 1
fi

export LD_LIBRARY_PATH="${REPO_ROOT}/thirdparty/sdk-shiftglue/lib:${REPO_ROOT}/out/build/linux-amd64-release:${LD_LIBRARY_PATH:-}"
exec "${FM4_BIN}" --game_data_root "${REPO_ROOT}/game/disc1" --user_data_root "${REPO_ROOT}/user" "$@"
