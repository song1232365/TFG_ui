#!/usr/bin/env bash
set -e

# 便捷评测脚本：直接使用系统生成的文件进行评测
# 使用方法：
#   bash run_eval_from_system.sh --project_name May [--output_file metrics.json]

# 解析参数
PROJECT_NAME=""
OUTPUT_FILE="metrics.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project_name) PROJECT_NAME="$2"; shift 2;;
    --output_file) OUTPUT_FILE="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [ -z "$PROJECT_NAME" ]; then
  echo "Usage: $0 --project_name <project_name> [--output_file <output_file>]"
  echo "  --project_name: 项目名称（如 May, Macron），对应 TalkingGaussian/data/<project_name>/"
  echo "  --output_file: 输出 JSON 文件路径（默认: metrics.json）"
  echo ""
  echo "说明："
  echo "  此脚本会自动查找："
  echo "  - 预测视频：static/videos/talkinggaussian_*.mp4（系统生成的视频）"
  echo "  - 真实视频：TalkingGaussian/data/<project_name>/<project_name>.mp4（训练用的原始视频）"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 查找预测视频（系统生成的视频）
PRED_VIDEOS_DIR="$PROJECT_ROOT/static/videos"
GT_VIDEO="$PROJECT_ROOT/TalkingGaussian/data/$PROJECT_NAME/${PROJECT_NAME}.mp4"

# 检查真实视频是否存在
if [ ! -f "$GT_VIDEO" ]; then
  echo "错误: 真实视频不存在: $GT_VIDEO"
  echo "请确保项目名称正确，且已完成数据预处理"
  exit 1
fi

# 查找所有匹配的预测视频
PRED_VIDEOS=$(find "$PRED_VIDEOS_DIR" -name "talkinggaussian_*.mp4" -type f | head -1)

if [ -z "$PRED_VIDEOS" ]; then
  echo "错误: 未找到预测视频（在 $PRED_VIDEOS_DIR 中查找 talkinggaussian_*.mp4）"
  echo "请先通过视频生成界面生成预测视频"
  exit 1
fi

echo "=========================================="
echo "TalkingGaussian 系统评测脚本"
echo "=========================================="
echo "项目名称: $PROJECT_NAME"
echo "真实视频: $GT_VIDEO"
echo "预测视频: $PRED_VIDEOS"
echo "输出文件: $OUTPUT_FILE"
echo "=========================================="

# 如果只有一个预测视频，直接使用
if [ $(echo "$PRED_VIDEOS" | wc -l) -eq 1 ]; then
  PRED_VIDEO="$PRED_VIDEOS"
  echo ""
  echo "使用单个预测视频进行评测..."
  bash "$SCRIPT_DIR/run_all_metrics.sh" \
    --pred_dir "$PRED_VIDEO" \
    --gt_dir "$GT_VIDEO" \
    --output_file "$OUTPUT_FILE"
else
  echo ""
  echo "找到多个预测视频，使用第一个: $(echo "$PRED_VIDEOS" | head -1)"
  PRED_VIDEO=$(echo "$PRED_VIDEOS" | head -1)
  bash "$SCRIPT_DIR/run_all_metrics.sh" \
    --pred_dir "$PRED_VIDEO" \
    --gt_dir "$GT_VIDEO" \
    --output_file "$OUTPUT_FILE"
fi

echo ""
echo "评测完成！结果保存在: $OUTPUT_FILE"



