#!/usr/bin/env bash
set -euo pipefail

# Installs SyncNet official repo into this project and downloads required weights.
# Target dir is fixed for reproducibility.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNCNET_DIR="$ROOT_DIR/third_party/syncnet_python"

mkdir -p "$ROOT_DIR/third_party"

if [[ ! -d "$SYNCNET_DIR/.git" ]]; then
  echo "Cloning syncnet_python into: $SYNCNET_DIR"
  git clone https://github.com/joonson/syncnet_python.git "$SYNCNET_DIR"
else
  echo "syncnet_python already exists: $SYNCNET_DIR"
fi

mkdir -p "$SYNCNET_DIR/data"
mkdir -p "$SYNCNET_DIR/detectors/s3fd/weights"

echo "Downloading SyncNet model + detector weights..."
# From syncnet_python/download_model.sh
wget -O "$SYNCNET_DIR/data/syncnet_v2.model" \
  http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model

wget -O "$SYNCNET_DIR/detectors/s3fd/weights/sfd_face.pth" \
  https://www.robots.ox.ac.uk/~vgg/software/lipsync/data/sfd_face.pth

echo "Done. SyncNet dir: $SYNCNET_DIR"
