# Docker 构建与运行说明

本文档说明如何构建和运行 TalkingGaussian UI 系统的 Docker 镜像。

## 一、镜像说明

本项目提供两个 Docker 镜像：

1. **主镜像 (`tfg_ui:latest`)**：包含完整的 Flask UI、训练、推理、实时对话功能
2. **评测镜像 (`tfg_ui:eval`)**：用于运行评测指标（NIQE, PSNR, FID, SSIM, LSE-C, LSE-D）

## 二、环境要求

- **Docker**：20.10+
- **Docker Compose**：1.29+（可选）
- **NVIDIA Docker**：支持 GPU（`nvidia-docker2` 或 `docker run --gpus all`）
- **GPU**：支持 CUDA 11.8+（推荐 NVIDIA GPU，至少 8GB 显存）

## 三、构建镜像

### 3.1 构建主镜像

```bash
# 在项目根目录执行
docker build -t tfg_ui:latest -f Dockerfile .
```

**构建时间**：约 30-60 分钟（取决于网络速度和硬件）

**镜像大小**：约 15-20 GB（包含所有 conda 环境和依赖）

### 3.2 构建评测镜像

```bash
# 先构建主镜像，然后构建评测镜像
docker build -t tfg_ui:latest -f Dockerfile .
docker build -t tfg_ui:eval -f Dockerfile.eval .
```

## 四、运行主系统

### 4.1 使用 Docker 命令运行

```bash
docker run -d \
  --name tfg_ui \
  --gpus all \
  -p 5001:5001 \
  -v $(pwd)/static:/app/static \
  -v $(pwd)/TalkingGaussian/data:/app/TalkingGaussian/data \
  -v $(pwd)/TalkingGaussian/output:/app/TalkingGaussian/output \
  -v $(pwd)/backend/config:/app/backend/config \
  tfg_ui:latest
```

### 4.2 使用 Docker Compose 运行

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4.3 访问系统

启动后，访问：http://localhost:5001

## 五、运行评测

### 5.1 准备数据

评测需要两个目录：
- **预测结果目录**：包含模型生成的视频文件（`.mp4`）
- **真实视频目录**：包含对应的真实视频文件（`.mp4`）

#### 方法一：使用系统生成的文件（推荐）

如果已经通过训练和视频生成界面生成了文件，可以直接使用：

```bash
# 预测视频位置：static/videos/talkinggaussian_*.mp4（视频生成界面生成）
# 真实视频位置：TalkingGaussian/data/<project_name>/<project_name>.mp4（训练用的原始视频）

# 使用便捷脚本（自动查找文件）
docker exec -it tfg_ui bash TalkingGaussian/evaluation/run_eval_from_system.sh \
  --project_name May \
  --output_file /app/static/metrics.json
```

#### 方法二：手动准备评测数据

```bash
# 创建评测数据目录
mkdir -p evaluation_pred evaluation_gt evaluation_output

# 将预测视频放入 evaluation_pred/
cp static/videos/talkinggaussian_*.mp4 evaluation_pred/

# 将真实视频放入 evaluation_gt/
cp TalkingGaussian/data/May/May.mp4 evaluation_gt/
```

### 5.2 运行评测

#### 方法一：使用评测镜像

```bash
docker run --rm \
  --gpus all \
  -v $(pwd)/evaluation_pred:/app/pred \
  -v $(pwd)/evaluation_gt:/app/gt \
  -v $(pwd)/evaluation_output:/app/output \
  tfg_ui:eval \
  --pred_dir /app/pred \
  --gt_dir /app/gt \
  --output_file /app/output/metrics.json
```

#### 方法二：在主容器中运行（使用系统生成的文件）

```bash
# 进入主容器
docker exec -it tfg_ui bash

# 方式A：使用便捷脚本（自动查找文件，推荐）
bash TalkingGaussian/evaluation/run_eval_from_system.sh \
  --project_name May \
  --output_file /app/static/metrics.json

# 方式B：手动指定路径
bash TalkingGaussian/evaluation/run_all_metrics.sh \
  --pred_dir /app/static/videos/talkinggaussian_tts_output_20251223_213711.mp4 \
  --gt_dir /app/TalkingGaussian/data/May/May.mp4 \
  --output_file /app/static/metrics.json
```

#### 方法三：在主容器中运行（使用手动准备的数据）

```bash
# 进入主容器
docker exec -it tfg_ui bash

# 运行评测脚本
bash TalkingGaussian/evaluation/run_all_metrics.sh \
  --pred_dir /app/pred \
  --gt_dir /app/gt \
  --output_file /app/output/metrics.json
```

### 5.3 查看评测结果

评测结果会保存在 `metrics.json` 文件中，包含以下指标：

```json
{
  "PSNR": 28.5,
  "SSIM": 0.92,
  "NIQE": 5.3,
  "FID": 12.4,
  "LSE-C": 6.8,
  "LSE-D": 7.2
}
```

## 六、数据目录说明

### 6.1 挂载目录

| 宿主机目录 | 容器目录 | 说明 |
|-----------|---------|------|
| `./static` | `/app/static` | 静态文件（上传的视频、生成的视频、音频等） |
| `./TalkingGaussian/data` | `/app/TalkingGaussian/data` | 训练数据目录 |
| `./TalkingGaussian/output` | `/app/TalkingGaussian/output` | 训练好的模型输出 |
| `./backend/config` | `/app/backend/config` | API 配置文件 |

### 6.2 数据准备

#### 训练数据

将训练视频放入 `static/uploads/videos/` 目录，系统会自动复制到 `TalkingGaussian/data/<video_name>/`。

#### 模型文件

训练完成后，模型保存在 `TalkingGaussian/output/<project_name>/` 目录。

#### 预训练模型

如果 CosyVoice 或 TalkingGaussian 需要预训练模型，建议：
- 通过 volume 挂载（推荐）
- 或在构建时下载（会增加镜像大小）

## 七、常见问题

### 7.1 GPU 不可用

**问题**：`docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]`

**解决**：
```bash
# 安装 nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 7.2 端口被占用

**问题**：`Error: bind: address already in use`

**解决**：
```bash
# 修改 docker-compose.yml 中的端口映射
ports:
  - "5002:5001"  # 改为其他端口
```

### 7.3 内存不足

**问题**：构建或运行时内存不足

**解决**：
- 增加 Docker 内存限制（Docker Desktop → Settings → Resources）
- 或使用 `--memory` 参数限制容器内存

### 7.4 评测脚本找不到 SyncNet

**问题**：LSE-C/LSE-D 指标无法计算

**解决**：
```bash
# 进入容器
docker exec -it tfg_ui bash

# 设置 SyncNet
cd TalkingGaussian/evaluation
bash setup_syncnet.sh
bash setup_lse.sh
```

## 八、开发模式

如果需要修改代码后重新构建：

```bash
# 停止容器
docker-compose down

# 重新构建（不使用缓存）
docker build --no-cache -t tfg_ui:latest -f Dockerfile .

# 启动容器
docker-compose up -d
```

## 九、生产部署建议

1. **使用环境变量**：将 API 密钥等敏感信息通过环境变量传入
2. **使用 secrets**：Docker Swarm 或 Kubernetes 的 secrets 管理
3. **日志管理**：配置日志轮转和集中日志收集
4. **资源限制**：设置 CPU、内存、GPU 限制
5. **健康检查**：添加健康检查端点

## 十、技术支持

如有问题，请查看：
- `项目运行环境说明.md`：环境配置详细说明
- `项目结构说明.md`：项目结构说明
- GitHub Issues：提交问题反馈

