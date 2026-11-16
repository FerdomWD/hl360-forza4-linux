#!/usr/bin/env bash
set -euo pipefail

CFG="${1:-release}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [ -d "${REPO_ROOT}/tools/cmake/bin" ]; then
  export PATH="${REPO_ROOT}/tools/cmake/bin:${PATH}"
fi

if [ -z "${REXSDK_ROOT:-}" ]; then
  if [ -f "${REPO_ROOT}/thirdparty/sdk-shiftglue/bin/rexglue" ]; then
    REXSDK_ROOT="${REPO_ROOT}/thirdparty/sdk-shiftglue"
  elif [ -f "${REPO_ROOT}/thirdparty/sdk/bin/rexglue" ]; then
    REXSDK_ROOT="${REPO_ROOT}/thirdparty/sdk"
  fi
fi

if [ -z "${REXSDK_ROOT:-}" ] || [ ! -f "${REXSDK_ROOT}/bin/rexglue" ]; then
  echo "Error: Set REXSDK_ROOT to a built ReXGlue / ShiftGlue SDK installation." >&2
  exit 1
fi

if [ ! -f "game/disc1/default.xex" ]; then
  for cand in \
    "${REPO_ROOT}/out/build/linux-amd64-${CFG}/game/default.xex" \
    "${REPO_ROOT}/out/build/linux-amd64-release/game/default.xex" \
    "${HOME}/Games/Forza Motorsport 4/linux-amd64-release/game/default.xex"; do
    if [ -f "${cand}" ]; then
      mkdir -p "${REPO_ROOT}/game"
      ln -sf "$(dirname "${cand}")" "${REPO_ROOT}/game/disc1"
      echo "Found game files at ${cand}, linked to game/disc1"
      break
    fi
  done
fi

if [ ! -f "generated/default/sources.cmake" ]; then
  if [ -f "game/disc1/default.xex" ]; then
    "${REXSDK_ROOT}/bin/rexglue" codegen fm4_manifest.toml
  else
    echo "Warning: game/disc1/default.xex not found. Extract Disc 1 first to run codegen for fm4."
    echo "Building launcher and tools only..."
    cmake --preset "linux-amd64-${CFG}" -DCMAKE_PREFIX_PATH="${REXSDK_ROOT}"
    cmake --build "out/build/linux-amd64-${CFG}" --target fm4-launcher fm4tool fm4-wheel-probe fm4-instant-launcher
    exit 0
  fi
fi

cmake --preset "linux-amd64-${CFG}" -DCMAKE_PREFIX_PATH="${REXSDK_ROOT}"
cmake --build "out/build/linux-amd64-${CFG}"

# If user installed to ~/Games/Forza Motorsport 4/linux-amd64-release, keep it updated
GAMES_DIR="${HOME}/Games/Forza Motorsport 4/linux-amd64-${CFG}"
if [ -d "${GAMES_DIR}" ]; then
  echo "Syncing updated binaries to ${GAMES_DIR}..."
  for b in fm4 fm4-launcher fm4tool fm4-wheel-probe "Forza Motorsport 4" librexgpu-fh1.so librexruntime.so; do
    if [ -f "out/build/linux-amd64-${CFG}/${b}" ]; then
      cp -fv --remove-destination "out/build/linux-amd64-${CFG}/${b}" "${GAMES_DIR}/${b}" || true
    fi
  done
fi
