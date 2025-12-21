import argparse
import glob
import os
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description="Calculate NIQE score using pyiqa")
    parser.add_argument("frames_dir", type=str, help="Directory containing the frames (png/jpg)")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device to use")
    args = parser.parse_args()

    # 检查 pyiqa 是否安装
    try:
        import pyiqa
    except ImportError:
        print("错误: 未找到 'pyiqa' 库。")
        print("请运行以下命令安装: pip install pyiqa")
        return

    # 获取图片列表
    extensions = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
    img_paths = []
    for ext in extensions:
        img_paths.extend(glob.glob(os.path.join(args.frames_dir, ext)))
    
    img_paths = sorted(img_paths)
    if not img_paths:
        print(f"在目录 {args.frames_dir} 中未找到图片。")
        return

    print(f"找到 {len(img_paths)} 张图片。正在加载 NIQE 模型...")

    # 初始化 NIQE 指标
    # pyiqa 会自动处理模型权重的下载和加载
    try:
        # as_loss=False 表示返回原始分数（通常越低越好）
        niqe_metric = pyiqa.create_metric('niqe', device=args.device, as_loss=False)
    except Exception as e:
        print(f"初始化 NIQE 失败: {e}")
        print("可能是网络问题导致无法下载模型权重，或者 pyiqa 版本不兼容。")
        return

    scores = []
    print(f"开始评估 (使用设备: {args.device})...")
    
    for img_path in tqdm(img_paths):
        try:
            # 读取图片并转换为 Tensor (1, C, H, W), 范围 [0, 1]
            img = Image.open(img_path).convert('RGB')
            img_np = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np).permute(2, 0, 1).unsqueeze(0).to(args.device)
            
            with torch.no_grad():
                score = niqe_metric(img_tensor)
                scores.append(score.item())
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")

    if scores:
        mean_score = np.mean(scores)
        print(f"\nNIQE (pyiqa) = {mean_score:.6f} (N={len(scores)})")
    else:
        print("未能计算任何图片的 NIQE 分数。")

if __name__ == "__main__":
    main()