# Evaluation

按你要求：
- 帧级指标只放在 `eval_frame_metrics.py`：PSNR / SSIM /（可选）LPIPS
- NIQE/FID/LSE 都是**独立脚本**，避免污染逐帧 loop 或训练循环

附加工具：
- `extract_frames.py`：视频抽帧成图片目录（给 NIQE/FID 用）
- `setup_syncnet.sh`：自动拉取 SyncNet 官方代码并下载权重到固定目录
- `setup_lse.sh`：在 SyncNet 基础上，额外拉取 Wav2Lip 的 `scores_LSE` 脚本并拷贝到 SyncNet 目录

## 依赖

- SSIM / NIQE：
  - `pip install scikit-image`
- FID（推荐）：
  - `pip install clean-fid`
  - 或者 `pip install torch-fidelity`

当前仓库的 `environment.yml` 已包含：`opencv-python`、`lpips`、`face_alignment`、`ffmpeg`。
本环境里我已确认：`scikit-image`、`lpips` 可用；`clean-fid`、`torch-fidelity` 默认未安装。

可选依赖文件：

```bash
pip install -r evaluation/requirements_eval.txt
```

## 1) 帧级指标（PSNR / SSIM / LPIPS）

对齐两段视频，按帧 zip 读取，输出均值。

```bash
python evaluation/eval_frame_metrics.py /path/to/pred.mp4 /path/to/gt.mp4
python evaluation/eval_frame_metrics.py /path/to/pred.mp4 /path/to/gt.mp4 --lpips
```

如果你只有视频、没有帧目录，可以先抽帧：

```bash
python evaluation/extract_frames.py /path/to/video.mp4 /path/to/out_frames
python evaluation/extract_frames.py /path/to/video.mp4 /path/to/out_frames --fps 25
```

## 2) NIQE（目录级）

输入：生成帧目录（图片序列），逐张 NIQE 再取平均。

```bash
python evaluation/eval_niqe.py /path/to/generated_frames
```

注意：你当前环境是 Python 3.7 + scikit-image 0.19.x 时，可能没有 `skimage.metrics.niqe`。本仓库脚本会自动 fallback 到 `piq`：

建议用单独的高版本 Python 评估环境跑 NIQE，例如：

```bash
conda create -n tg_niqe python=3.10 -y
conda activate tg_niqe
pip install -U scikit-image opencv-python numpy
python evaluation/eval_niqe.py /path/to/generated_frames
```

## 3) FID（目录级）

注意：FID 必须是“目录级别算”。

- clean-fid（推荐）

```bash
python evaluation/eval_fid.py /path/to/gen_frames /path/to/gt_frames
```

- torch-fidelity（可选）

```bash
python evaluation/eval_fid.py /path/to/gen_frames /path/to/gt_frames --backend torch-fidelity
```

## 4) LSE-C / LSE-D（SyncNet 官方实现）

本仓库未内置 SyncNet 官方代码；`eval_lse.py` 仅做安全包装调用。

### 需要的外部代码/权重

- 代码仓库（官方 SyncNet demo）：
  - https://github.com/joonson/syncnet_python
- 该仓库的 `download_model.sh` 里列出的权重 URL：
  - SyncNet 模型：`http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model`
  - S3FD 人脸检测权重：`https://www.robots.ox.ac.uk/~vgg/software/lipsync/data/sfd_face.pth`

我已提供一键脚本，会把代码/权重放到固定目录（推荐）：

```bash
bash evaluation/setup_syncnet.sh
```

如果你要按 Wav2Lip 论文里的 LSE-C/LSE-D 跑分（推荐），再执行：

```bash
bash evaluation/setup_lse.sh
```

权重所在服务器目录（你本地下载后也可以手动上传到这里）：

- `/root/TalkingGaussian/third_party/syncnet_python/data/syncnet_v2.model`
- `/root/TalkingGaussian/third_party/syncnet_python/detectors/s3fd/weights/sfd_face.pth`

### 运行方式（目录级）

LSE 评测是对“一个目录里的所有生成视频”计算分数（不是逐帧/单视频 loop 指标）。

```bash
python evaluation/eval_lse.py /path/to/generated_videos_dir --preset wav2lip-real
```

你需要自行准备 SyncNet 官方 repo，并给出可运行命令（使用 `{video}` 占位符）。示例：

```bash
python evaluation/eval_lse.py /path/to/generated.mp4 \
  --cmd 'python /path/to/SyncNet/run_pipeline.py --videofile {video} && python /path/to/SyncNet/calc_scores.py --videofile {video}'
```

脚本会直接透传输出；如果 SyncNet 的命令行参数与你的版本不同，按官方 README 调整即可。
