#!/usr/bin/env bash
set -e

# 统一评测脚本：运行所有指标（NIQE, PSNR, FID, SSIM, LSE-C, LSE-D）
# 使用方法：
#   bash run_all_metrics.sh --pred_dir /path/to/pred --gt_dir /path/to/gt [--output_file metrics.json]

# 解析参数
PRED_DIR=""
GT_DIR=""
OUTPUT_FILE="metrics.json"
EXTRACT_FRAMES=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pred_dir) PRED_DIR="$2"; shift 2;;
    --gt_dir) GT_DIR="$2"; shift 2;;
    --output_file) OUTPUT_FILE="$2"; shift 2;;
    --no_extract_frames) EXTRACT_FRAMES=false; shift;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [ -z "$PRED_DIR" ] || [ -z "$GT_DIR" ]; then
  echo "Usage: $0 --pred_dir <pred_dir> --gt_dir <gt_dir> [--output_file <output_file>]"
  echo "  --pred_dir: 预测视频目录或单个视频文件"
  echo "  --gt_dir: 真实视频目录或单个视频文件"
  echo "  --output_file: 输出 JSON 文件路径（默认: metrics.json）"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$SCRIPT_DIR/_work"
mkdir -p "$WORK_DIR"

echo "=========================================="
echo "TalkingGaussian 统一评测脚本"
echo "=========================================="
echo "预测目录/文件: $PRED_DIR"
echo "真实目录/文件: $GT_DIR"
echo "输出文件: $OUTPUT_FILE"
echo "=========================================="

# 初始化结果变量
PSNR_VAL="null"
SSIM_VAL="null"
NIQE_VAL="null"
FID_VAL="null"
LSE_C_VAL="null"
LSE_D_VAL="null"

# 1. 提取帧（如果需要）
if [ "$EXTRACT_FRAMES" = true ]; then
  echo ""
  echo "[1/6] 提取视频帧..."
  
  PRED_FRAMES="$WORK_DIR/pred_frames"
  GT_FRAMES="$WORK_DIR/gt_frames"
  mkdir -p "$PRED_FRAMES" "$GT_FRAMES"
  
  # 判断是目录还是单个文件
  if [ -d "$PRED_DIR" ]; then
    # 目录：提取所有视频的第一帧或合并所有帧
    for video in "$PRED_DIR"/*.mp4; do
      if [ -f "$video" ]; then
        name=$(basename "$video" .mp4)
        conda run -n talking_gaussian --no-capture-output \
          python "$SCRIPT_DIR/extract_frames.py" "$video" "$PRED_FRAMES/$name"
      fi
    done
  else
    # 单个文件
    name=$(basename "$PRED_DIR" .mp4)
    conda run -n talking_gaussian --no-capture-output \
      python "$SCRIPT_DIR/extract_frames.py" "$PRED_DIR" "$PRED_FRAMES/$name"
  fi
  
  if [ -d "$GT_DIR" ]; then
    for video in "$GT_DIR"/*.mp4; do
      if [ -f "$video" ]; then
        name=$(basename "$video" .mp4)
        conda run -n talking_gaussian --no-capture-output \
          python "$SCRIPT_DIR/extract_frames.py" "$video" "$GT_FRAMES/$name"
      fi
    done
  else
    name=$(basename "$GT_DIR" .mp4)
    conda run -n talking_gaussian --no-capture-output \
      python "$SCRIPT_DIR/extract_frames.py" "$GT_DIR" "$GT_FRAMES/$name"
  fi
  
  echo "✓ 帧提取完成"
fi

# 2. PSNR / SSIM（帧级指标）
echo ""
echo "[2/6] 计算 PSNR / SSIM..."
if [ -f "$PRED_DIR" ] && [ -f "$GT_DIR" ]; then
  # 单个视频文件
  OUTPUT=$(conda run -n talking_gaussian --no-capture-output \
    python "$SCRIPT_DIR/eval_frame_metrics.py" "$PRED_DIR" "$GT_DIR" 2>&1)
  PSNR_VAL=$(echo "$OUTPUT" | grep -oP "PSNR\s*=\s*\K[0-9.]+" || echo "null")
  SSIM_VAL=$(echo "$OUTPUT" | grep -oP "SSIM\s*=\s*\K[0-9.]+" || echo "null")
  echo "✓ PSNR: $PSNR_VAL, SSIM: $SSIM_VAL"
else
  echo "⚠ PSNR/SSIM 需要单个视频文件，跳过（目录模式暂不支持）"
fi

# 3. NIQE（目录级）
echo ""
echo "[3/6] 计算 NIQE..."
if [ -d "$PRED_FRAMES" ] && [ "$(ls -A $PRED_FRAMES 2>/dev/null)" ]; then
  # 合并所有帧目录
  ALL_PRED_FRAMES="$WORK_DIR/all_pred_frames"
  mkdir -p "$ALL_PRED_FRAMES"
  find "$PRED_FRAMES" -type f \( -name "*.jpg" -o -name "*.png" \) -exec cp {} "$ALL_PRED_FRAMES/" \;
  
  if [ "$(ls -A $ALL_PRED_FRAMES 2>/dev/null)" ]; then
    OUTPUT=$(conda run -n tg_niqe --no-capture-output \
      python "$SCRIPT_DIR/eval_niqe.py" "$ALL_PRED_FRAMES" 2>&1)
    NIQE_VAL=$(echo "$OUTPUT" | grep -oP "NIQE[^=]*=\s*\K[0-9.]+" || echo "null")
    echo "✓ NIQE: $NIQE_VAL"
  else
    echo "⚠ 未找到有效帧文件"
  fi
else
  echo "⚠ NIQE 需要帧目录，跳过"
fi

# 4. FID（目录级）
echo ""
echo "[4/6] 计算 FID..."
if [ -d "$PRED_FRAMES" ] && [ -d "$GT_FRAMES" ] && \
   [ "$(ls -A $PRED_FRAMES 2>/dev/null)" ] && [ "$(ls -A $GT_FRAMES 2>/dev/null)" ]; then
  # 合并所有帧
  ALL_PRED_FRAMES="$WORK_DIR/all_pred_frames"
  ALL_GT_FRAMES="$WORK_DIR/all_gt_frames"
  mkdir -p "$ALL_PRED_FRAMES" "$ALL_GT_FRAMES"
  find "$PRED_FRAMES" -type f \( -name "*.jpg" -o -name "*.png" \) -exec cp {} "$ALL_PRED_FRAMES/" \;
  find "$GT_FRAMES" -type f \( -name "*.jpg" -o -name "*.png" \) -exec cp {} "$ALL_GT_FRAMES/" \;
  
  if [ "$(ls -A $ALL_PRED_FRAMES 2>/dev/null)" ] && [ "$(ls -A $ALL_GT_FRAMES 2>/dev/null)" ]; then
    OUTPUT=$(conda run -n tg_eval --no-capture-output \
      python "$SCRIPT_DIR/eval_fid.py" "$ALL_PRED_FRAMES" "$ALL_GT_FRAMES" 2>&1)
    FID_VAL=$(echo "$OUTPUT" | grep -oP "FID[^=]*=\s*\K[0-9.]+" || echo "null")
    echo "✓ FID: $FID_VAL"
  else
    echo "⚠ 未找到有效帧文件"
  fi
else
  echo "⚠ FID 需要预测和真实帧目录，跳过"
fi

# 5. LSE-C / LSE-D（需要 SyncNet）
echo ""
echo "[5/6] 计算 LSE-C / LSE-D..."
if [ -d "$PRED_DIR" ] || [ -f "$PRED_DIR" ]; then
  # 检查 SyncNet 是否已设置
  if [ -f "$SCRIPT_DIR/../third_party/syncnet_python/run_pipeline.py" ]; then
    OUTPUT=$(conda run -n talking_gaussian --no-capture-output \
      python "$SCRIPT_DIR/eval_lse.py" "$PRED_DIR" --preset wav2lip-real 2>&1 || echo "")
    LSE_C_VAL=$(echo "$OUTPUT" | grep -oP "LSE-C[^=]*=\s*\K[0-9.]+" || echo "null")
    LSE_D_VAL=$(echo "$OUTPUT" | grep -oP "LSE-D[^=]*=\s*\K[0-9.]+" || echo "null")
    echo "✓ LSE-C: $LSE_C_VAL, LSE-D: $LSE_D_VAL"
  else
    echo "⚠ SyncNet 未设置，跳过 LSE 指标"
    echo "  运行: bash $SCRIPT_DIR/setup_syncnet.sh 和 bash $SCRIPT_DIR/setup_lse.sh"
  fi
else
  echo "⚠ LSE 需要视频目录或文件，跳过"
fi

# 生成 JSON 结果
cat > "$OUTPUT_FILE" <<EOF
{
  "PSNR": $PSNR_VAL,
  "SSIM": $SSIM_VAL,
  "NIQE": $NIQE_VAL,
  "FID": $FID_VAL,
  "LSE-C": $LSE_C_VAL,
  "LSE-D": $LSE_D_VAL
}
EOF

# 输出结果
echo ""
echo "=========================================="
echo "评测完成！"
echo "=========================================="
cat "$OUTPUT_FILE" | python -m json.tool 2>/dev/null || cat "$OUTPUT_FILE"
echo ""
echo "结果已保存到: $OUTPUT_FILE"

