#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <Disc 1.iso> [<Disc 2.iso>]" >&2
  exit 1
fi

PLAY_ISO="$(realpath "$1")"
CONTENT_ISO="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

FM4_TOOL="${REPO_ROOT}/out/build/linux-amd64-release/fm4tool"
if [ ! -f "${FM4_TOOL}" ]; then
  echo "Error: fm4tool not found. Run scripts/build.sh first." >&2
  exit 1
fi

mkdir -p "${REPO_ROOT}/game/disc1" "${REPO_ROOT}/user"
echo "Extracting Disc 1 (Play Disc)..."
"${FM4_TOOL}" iso "${PLAY_ISO}" "${REPO_ROOT}/game/disc1"

if [ -n "${CONTENT_ISO}" ]; then
  CONTENT_ISO="$(realpath "${CONTENT_ISO}")"
  mkdir -p "${REPO_ROOT}/game/disc2"
  echo "Extracting Disc 2 (Content Disc)..."
  "${FM4_TOOL}" iso "${CONTENT_ISO}" "${REPO_ROOT}/game/disc2"
  echo "Installing Disc 2 DLC packages..."
  "${FM4_TOOL}" install-dlc "${REPO_ROOT}/game/disc1" "${REPO_ROOT}/game/disc2" "${REPO_ROOT}/user"
fi

echo "Game installation complete."
