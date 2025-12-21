#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THIRD_PARTY="$ROOT_DIR/third_party"
SYNCNET_DIR="$THIRD_PARTY/syncnet_python"
WAV2LIP_DIR="$THIRD_PARTY/Wav2Lip"
MODEL_PATH="$SYNCNET_DIR/data/syncnet_v2.model"

# 1. Setup SyncNet (Clone + Models)
# 修改：检查模型文件是否存在，而不是只检查目录
if [[ -f "$MODEL_PATH" ]]; then
    echo "SyncNet model found at $MODEL_PATH. Skipping setup_syncnet.sh."
else
    echo "SyncNet model not found. Running setup_syncnet.sh..."
    # 注意：如果目录存在但模型不存在，setup_syncnet.sh 中的 git clone 可能会报错，
    # 但随后的下载步骤应该能正常执行。
    bash "$ROOT_DIR/evaluation/setup_syncnet.sh"
fi

mkdir -p "$THIRD_PARTY"

# 2. Setup Wav2Lip (for evaluation scripts)
if [[ ! -d "$WAV2LIP_DIR" ]]; then
  echo "Cloning Wav2Lip into: $WAV2LIP_DIR"
  git clone https://github.com/Rudrabha/Wav2Lip.git "$WAV2LIP_DIR"
else
  echo "Wav2Lip already exists."
fi

if [[ ! -d "$WAV2LIP_DIR/evaluation/scores_LSE" ]]; then
  echo "ERROR: scores_LSE not found in cloned Wav2Lip repo." >&2
  exit 2
fi

# 3. Copy scripts
echo "Copying LSE evaluation scripts into syncnet_python..."
cp -v "$WAV2LIP_DIR"/evaluation/scores_LSE/*.py "$SYNCNET_DIR"/
cp -v "$WAV2LIP_DIR"/evaluation/scores_LSE/*.sh "$SYNCNET_DIR"/ || true

if [[ -f "$SYNCNET_DIR/calculate_scores_real_videos.sh" ]]; then
    chmod +x "$SYNCNET_DIR/calculate_scores_real_videos.sh"
fi

echo "Done."