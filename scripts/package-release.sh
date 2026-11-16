#!/usr/bin/env bash
# Packages a Linux release build into out/releases/FM4-<version>-linux-amd64.tar.gz
# Usage: ./scripts/package-release.sh [version] [build_dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

VERSION="${1:-v0.3.11-linux}"
BUILD_DIR="${2:-out/build/linux-amd64-release}"
SDK_SOURCE="thirdparty/shiftglue-src"

if [ ! -d "${BUILD_DIR}" ]; then
  echo "Error: Build directory '${BUILD_DIR}' not found. Run ./scripts/build.sh release first." >&2
  exit 1
fi

for bin in "fm4" "fm4-launcher" "fm4tool" "fm4-wheel-probe" "Forza Motorsport 4"; do
  if [ ! -f "${BUILD_DIR}/${bin}" ]; then
    echo "Error: Missing '${bin}' in '${BUILD_DIR}'. Build release first." >&2
    exit 1
  fi
done

STAGE_DIR="${REPO_ROOT}/out/releases/${VERSION}-release"
DEST_DIR="${STAGE_DIR}/FM4"

rm -rf "${STAGE_DIR}"
mkdir -p "${DEST_DIR}/resources" "${DEST_DIR}/doc/img" "${DEST_DIR}/licenses/SDL3"

echo "Staging binaries and libraries..."
for bin in "fm4" "fm4-launcher" "fm4tool" "fm4-wheel-probe" "Forza Motorsport 4"; do
  cp -p "${BUILD_DIR}/${bin}" "${DEST_DIR}/"
  chmod +x "${DEST_DIR}/${bin}"
done

# Copy shared libraries (*.so)
for so in "${BUILD_DIR}"/*.so; do
  if [ -f "${so}" ]; then
    cp -p "${so}" "${DEST_DIR}/"
  fi
done

# Copy configuration and setup files (NO user-specific fm4.user.toml or copyrighted game files)
for f in "fm4.toml" "game_files.sha256" "install-forza-plus.py" "uninstall-forza-plus.py" "fm4pc.ico"; do
  if [ -f "${BUILD_DIR}/${f}" ]; then
    cp -p "${BUILD_DIR}/${f}" "${DEST_DIR}/"
  elif [ -f "${REPO_ROOT}/${f}" ]; then
    cp -p "${REPO_ROOT}/${f}" "${DEST_DIR}/"
  fi
done

if [ -d "${BUILD_DIR}/resources" ]; then
  cp -rp "${BUILD_DIR}/resources/"* "${DEST_DIR}/resources/"
elif [ -d "${REPO_ROOT}/resources" ]; then
  cp -rp "${REPO_ROOT}/resources/"* "${DEST_DIR}/resources/"
fi

# Documentation and licenses
if [ -f "${REPO_ROOT}/README.md" ]; then
  cp -p "${REPO_ROOT}/README.md" "${DEST_DIR}/"
fi
if [ -d "${REPO_ROOT}/doc" ]; then
  cp -rp "${REPO_ROOT}/doc/"* "${DEST_DIR}/doc/" 2>/dev/null || true
fi
if [ -f "${SDK_SOURCE}/LICENSE" ]; then
  cp -p "${SDK_SOURCE}/LICENSE" "${DEST_DIR}/licenses/ShiftGlue-SDK.txt"
fi
if [ -f "${SDK_SOURCE}/thirdparty/sdl3/LICENSE.txt" ]; then
  cp -p "${SDK_SOURCE}/thirdparty/sdl3/LICENSE.txt" "${DEST_DIR}/licenses/SDL3/LICENSE.txt"
fi

# Generate SHA256 checksums of payload
(
  cd "${DEST_DIR}"
  find . -type f ! -name "SHA256SUMS.txt" -printf '%P\n' | sort | while read -r f; do
    sha256sum "${f}"
  done > SHA256SUMS.txt
)

# Create tar.gz and zip archives
OUT_DIR="${REPO_ROOT}/out/releases"
mkdir -p "${OUT_DIR}"
TAR_NAME="FM4-${VERSION}-linux-amd64.tar.gz"
ZIP_NAME="FM4-${VERSION}-linux-amd64.zip"

echo "Creating ${TAR_NAME}..."
(
  cd "${STAGE_DIR}"
  tar -czf "${OUT_DIR}/${TAR_NAME}" "FM4"
)
sha256sum "${OUT_DIR}/${TAR_NAME}" > "${OUT_DIR}/${TAR_NAME}.sha256"

if command -v zip >/dev/null 2>&1; then
  echo "Creating ${ZIP_NAME}..."
  (
    cd "${STAGE_DIR}"
    zip -q -r -9 "${OUT_DIR}/${ZIP_NAME}" "FM4"
  )
  sha256sum "${OUT_DIR}/${ZIP_NAME}" > "${OUT_DIR}/${ZIP_NAME}.sha256"
fi

echo "=========================================================="
echo "Release successfully packaged in ${OUT_DIR}/:"
ls -lh "${OUT_DIR}/${TAR_NAME}"
echo "SHA-256: $(cat "${OUT_DIR}/${TAR_NAME}.sha256")"
echo "=========================================================="
