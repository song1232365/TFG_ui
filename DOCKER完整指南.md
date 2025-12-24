# TalkingGaussian UI - Docker 完整指南

本文档包含 Docker 相关的所有内容：安装、构建、运行、优化和故障排除。

---

## 目录

1. [一、Docker 安装](#一docker-安装)
2. [二、构建镜像](#二构建镜像)
3. [三、运行容器](#三运行容器)
4. [四、构建优化](#四构建优化)
5. [五、评测功能](#五评测功能)
6. [六、故障排除](#六故障排除)
7. [七、生产部署](#七生产部署)

---

## 一、Docker 安装

### 1.1 环境要求

- **操作系统**：Ubuntu 20.04+ / CentOS 7+ / Windows 10/11（64位）
- **Docker**：20.10+
- **Docker Compose**：1.29+（可选）
- **NVIDIA Docker**：支持 GPU
  - Linux：`nvidia-docker2`
  - Windows：Docker Desktop with WSL 2
- **GPU**：支持 CUDA 11.8+（推荐 NVIDIA GPU，至少 8GB 显存）

### 1.1.1 Windows系统：Docker Desktop启动（重要！）

**在Windows系统上，必须先启动Docker Desktop才能使用Docker命令。**

#### 启动Docker Desktop

**方法1：通过开始菜单**
1. 打开"开始"菜单
2. 搜索"Docker Desktop"并启动

**方法2：通过命令行**
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

**方法3：通过系统托盘**
- 查找系统托盘中的Docker图标并点击

#### 等待启动完成

- Docker Desktop启动需要30秒到2分钟
- 系统托盘图标从"正在启动"变为"运行中"（绿色）
- 启动完成后才能使用Docker命令

#### 验证Docker可用

```powershell
# 验证Docker是否运行
docker ps

# 检查版本
docker --version
```

**常见错误**：
```
ERROR: error during connect: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**解决方法**：
- 确保Docker Desktop已完全启动
- 检查WSL 2是否已安装：`wsl --version`
- 如果未安装：以管理员身份运行 `wsl --install`，然后重启电脑

#### Windows系统要求

- **Windows版本**：Windows 10 64位（2004+）或 Windows 11
- **WSL 2**：必须安装（`wsl --install`）
- **虚拟化**：在BIOS中启用虚拟化功能

### 1.2 快速安装（推荐）

使用一键安装脚本（适用于 Ubuntu/Debian）：

```bash
cd /root/TFG_ui
sudo ./install_docker_china.sh
```

**安装时间**：约 10-20 分钟

### 1.3 手动安装步骤

#### Ubuntu/Debian 系统

```bash
# 1. 安装 Docker（使用 Ubuntu 官方仓库，更稳定）
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# 2. 安装 NVIDIA Docker 支持
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. 验证安装
docker --version
docker-compose --version
sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 1.4 配置用户权限（推荐）

避免每次使用 `sudo`：

```bash
sudo usermod -aG docker $USER
newgrp docker  # 或重新登录

# 验证（不需要 sudo）
docker ps
```

### 1.5 配置 Docker 镜像加速（推荐）

解决网络问题，加速镜像拉取：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

sudo systemctl restart docker
```

### 1.6 验证安装

```bash
# 检查 Docker 版本
docker --version
# 预期：Docker version 26.x.x

# 检查 Docker Compose
docker-compose --version
# 预期：docker-compose version 1.25.0

# 测试 GPU 支持
sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
# 应该显示 GPU 信息
```

---

## 二、构建镜像

### 2.1 镜像说明

本项目提供两个 Docker 镜像：

1. **主镜像 (`tfg_ui:latest`)**：包含完整的 Flask UI、训练、推理、实时对话功能
2. **评测镜像 (`tfg_ui:eval`)**：用于运行评测指标（NIQE, PSNR, FID, SSIM, LSE-C, LSE-D）

### 2.2 构建主镜像

**重要：构建前必须完成以下准备工作**

#### 步骤1：Windows系统 - 启动Docker Desktop

```powershell
# 确保Docker Desktop正在运行
docker ps

# 如果报错，启动Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# 等待30秒到2分钟，直到Docker Desktop完全启动
```

#### 步骤2：初始化Git子模块

在构建Docker镜像之前，必须先初始化Git子模块：

**Windows PowerShell**：
```powershell
cd "E:\STUDY\0-BIT\5-Y3-1\7-Speech Recognition and Synthesis\TFG_ui\TalkingGaussian"

# 初始化并更新子模块
git submodule update --init --recursive

# 如果遇到错误：fatal: No url found for submodule path 'xxx' in .gitmodules
# 请参考"项目配置文档.md"的2.3节进行修复

# 如果子模块目录为空，需要手动克隆（见项目配置文档.md 2.3节）

# 返回项目根目录
cd ..
```

**Linux系统**：
```bash
cd /root/TFG_ui

# 进入TalkingGaussian目录
cd TalkingGaussian

# 初始化并更新子模块
git submodule update --init --recursive

# 返回项目根目录
cd ..
```

#### 步骤3：构建镜像

**Windows PowerShell**：
```powershell
# 返回项目根目录
cd "E:\STUDY\0-BIT\5-Y3-1\7-Speech Recognition and Synthesis\TFG_ui"

# 构建镜像（推荐：保存日志）
docker build -t tfg_ui:latest -f Dockerfile . 2>&1 | Tee-Object -FilePath build.log

# 或者直接构建
docker build -t tfg_ui:latest -f Dockerfile .
```

**Linux系统**：
```bash
# 首次构建（建立缓存，约 30-60 分钟）
docker build -t tfg_ui:latest -f Dockerfile .

# 查看构建进度（可选）
docker build --progress=plain -t tfg_ui:latest -f Dockerfile .
```

**构建时间**：
- **首次构建**：30-60 分钟（所有层都需要构建）
- **代码修改后**：5-15 分钟（复用环境缓存，节省 70-80% 时间）

**镜像大小**：约 15-20 GB（包含所有 conda 环境和依赖）

**常见问题**：
- 如果构建时提示找不到子模块目录，请确保已执行 `git submodule update --init --recursive`
- 如果子模块初始化失败，请参考 `项目配置文档.md` 的 2.3 节进行修复

### 2.3 构建评测镜像

```bash
# 先构建主镜像
docker build -t tfg_ui:latest -f Dockerfile .

# 然后构建评测镜像
docker build -t tfg_ui:eval -f Dockerfile.eval .
```

### 2.4 Dockerfile 结构说明

```dockerfile
# 层 1-2：基础环境（几乎不变，缓存命中率高）
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04
RUN apt-get install ...  # 系统依赖

# 层 3：Miniconda（几乎不变，缓存命中率高）
RUN wget ... miniconda.sh

# 层 4：复制依赖文件（如果文件不变，缓存命中）
COPY requirements.txt /app/
COPY TalkingGaussian/environment.yml /app/TalkingGaussian/
...

# 层 5-8：创建 conda 环境（耗时，但如果依赖文件不变，可以复用缓存）
RUN conda env create -f TalkingGaussian/environment.yml  # 约 10-20 分钟
RUN conda create -n cosyvoice ...  # 约 5-10 分钟
RUN conda create -n tg_eval ...  # 约 3-5 分钟
RUN conda create -n tg_niqe ...  # 约 1-2 分钟

# 层 9：复制整个项目（代码变化时会失效）
COPY . /app/

# 层 10-11：安装 Flask 依赖和编译扩展（如果代码不变，可以复用）
RUN pip install -r requirements.txt  # 约 1-2 分钟
RUN pip install ./submodules/...  # 约 5-10 分钟（编译 CUDA 扩展）
```

---

## 三、运行容器

### 3.1 使用 Docker Compose（推荐）

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 重启服务
docker compose restart
```

### 3.2 使用 Docker 命令

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

### 3.3 访问系统

启动后，访问：http://localhost:5001

### 3.4 数据目录说明

| 宿主机目录 | 容器目录 | 说明 |
|-----------|---------|------|
| `./static` | `/app/static` | 静态文件（上传的视频、生成的视频、音频等） |
| `./TalkingGaussian/data` | `/app/TalkingGaussian/data` | 训练数据目录 |
| `./TalkingGaussian/output` | `/app/TalkingGaussian/output` | 训练好的模型输出 |
| `./backend/config` | `/app/backend/config` | API 配置文件 |

---

## 四、构建优化

### 4.1 Docker 缓存机制

Docker 使用**层缓存（Layer Caching）**机制：
- 每个 `RUN`、`COPY`、`ADD` 等指令都会创建一个新的层
- 如果指令和文件内容没有变化，Docker 会复用缓存的层
- **一旦某一层失效，后续所有层都需要重新构建**

### 4.2 缓存失效规则

| 操作 | 影响范围 | 构建时间 |
|-----|---------|---------|
| **修改 Python 代码** | 仅 `COPY . /app/` 及之后的层 | 5-15 分钟（复用环境缓存） |
| **修改 requirements.txt** | 从复制 requirements.txt 开始的所有层 | 20-40 分钟 |
| **修改 environment.yml** | 从复制 environment.yml 开始的所有层 | 25-50 分钟 |
| **修改 Dockerfile** | 从修改的指令开始的所有层 | 根据修改位置决定 |

### 4.3 最佳实践

#### 策略：先构建基础环境，再修改代码

```bash
# 步骤 1：首次完整构建（30-60 分钟）
docker build -t tfg_ui:latest -f Dockerfile .

# 步骤 2：修改代码（Python 文件、HTML 模板等）
# ... 修改 app.py, backend/*.py, templates/*.html ...

# 步骤 3：重新构建（5-15 分钟，复用缓存）
docker build -t tfg_ui:latest -f Dockerfile .
```

**效果**：
- ✅ 环境安装层（层 1-8）可以复用缓存
- ✅ 只重新复制代码和编译扩展模块
- ✅ 构建时间从 30-60 分钟减少到 5-15 分钟

### 4.4 查看缓存使用情况

```bash
# 构建时显示缓存使用情况
docker build --progress=plain -t tfg_ui:latest -f Dockerfile .

# 输出示例：
# #5 [3/11] RUN conda env create ...
# #5 CACHED  ← 表示使用了缓存
# #9 [7/11] COPY . /app/
# #9 DONE 0.5s  ← 表示重新构建（因为代码变化）
```

### 4.5 清理缓存

```bash
# 清理未使用的构建缓存
docker builder prune

# 清理所有缓存（包括正在使用的）
docker builder prune -a
```

---

## 五、评测功能

### 5.1 评测指标

| 指标 | 类型 | 输入 | 说明 |
|-----|------|------|------|
| **PSNR** | 帧级 | 两个视频文件 | 峰值信噪比，值越大越好 |
| **SSIM** | 帧级 | 两个视频文件 | 结构相似性，值越大越好（0-1） |
| **NIQE** | 目录级 | 预测视频帧目录 | 无参考图像质量评估，值越小越好 |
| **FID** | 目录级 | 预测帧目录 + 真实帧目录 | Fréchet距离，值越小越好 |
| **LSE-C** | 视频级 | 预测视频目录 | 唇形同步误差（连续），值越小越好 |
| **LSE-D** | 视频级 | 预测视频目录 | 唇形同步误差（离散），值越小越好 |

### 5.2 评测数据准备

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

### 5.3 运行评测

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

### 5.4 查看评测结果

评测结果会保存在 `metrics.json` 文件中：

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

### 5.5 评测流程说明

完整评测流程请参考：`TalkingGaussian/evaluation/评测流程说明.md`

---

## 六、故障排除

### 6.1 GPU 不可用

**问题**：`docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]`

**解决**：
```bash
# 检查 nvidia-docker2 是否安装
dpkg -l | grep nvidia-docker

# 检查 Docker daemon 配置
cat /etc/docker/daemon.json

# 重启 Docker
sudo systemctl restart docker

# 如果仍未解决，重新安装 nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 6.2 端口被占用

**问题**：`Error: bind: address already in use`

**解决**：
```bash
# 修改 docker-compose.yml 中的端口映射
ports:
  - "5002:5001"  # 改为其他端口

# 或停止占用端口的进程
sudo lsof -i :5001
sudo kill -9 <PID>
```

### 6.3 内存不足

**问题**：构建或运行时内存不足

**解决**：
- 增加 Docker 内存限制（Docker Desktop → Settings → Resources）
- 或使用 `--memory` 参数限制容器内存
- 清理未使用的镜像和容器：`docker system prune -a`

### 6.4 构建失败

**问题**：构建过程中出错

**解决**：
1. **查看详细错误**：
   ```bash
   docker build --progress=plain -t tfg_ui:latest -f Dockerfile . 2>&1 | tee build.log
   ```

2. **检查网络连接**：
   ```bash
   ping download.docker.com
   ```

3. **清理缓存重新构建**（如果怀疑缓存问题）：
   ```bash
   docker builder prune
   docker build --no-cache -t tfg_ui:latest -f Dockerfile .
   ```

### 6.5 评测脚本找不到 SyncNet

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

### 6.6 代理配置问题

**问题**：无法连接 Docker 仓库或拉取镜像

**解决**：
```bash
# 检查代理配置
cat /etc/apt/apt.conf.d/proxy.conf

# 如果代理服务未运行，注释掉代理配置
sudo nano /etc/apt/apt.conf.d/proxy.conf
# 添加 # 注释掉代理行

# 配置 Docker 镜像加速（推荐）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF
sudo systemctl restart docker
```

### 6.7 无法使用 docker 命令（需要 sudo）

**问题**：每次都需要使用 `sudo docker`

**解决**：
```bash
# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录或使用
newgrp docker

# 验证（不需要 sudo）
docker ps
```

---

## 七、生产部署

### 7.1 开发调试流程

```bash
# 1. 首次构建（建立缓存）
docker build -t tfg_ui:latest -f Dockerfile .

# 2. 运行测试
docker compose up -d

# 3. 修改代码
# ... 修改 app.py, backend/*.py 等 ...

# 4. 重新构建（快速，复用缓存）
docker build -t tfg_ui:latest -f Dockerfile .

# 5. 重启容器
docker compose restart
```

### 7.2 生产部署流程

```bash
# 1. 构建最终镜像
docker build -t tfg_ui:latest -f Dockerfile .

# 2. 保存镜像（可选，用于迁移）
docker save tfg_ui:latest | gzip > tfg_ui_latest.tar.gz

# 3. 运行容器
docker compose up -d

# 4. 查看状态
docker compose ps
docker compose logs -f
```

### 7.3 部署建议

1. **使用环境变量**：将 API 密钥等敏感信息通过环境变量传入
2. **使用 secrets**：Docker Swarm 或 Kubernetes 的 secrets 管理
3. **日志管理**：配置日志轮转和集中日志收集
4. **资源限制**：设置 CPU、内存、GPU 限制
5. **健康检查**：添加健康检查端点
6. **备份策略**：定期备份模型和数据目录

### 7.4 镜像迁移

```bash
# 导出镜像
docker save tfg_ui:latest | gzip > tfg_ui_latest.tar.gz

# 在另一台机器上导入
gunzip -c tfg_ui_latest.tar.gz | docker load

# 运行
docker run -d --gpus all -p 5001:5001 tfg_ui:latest
```

---

## 八、快速参考

### 8.1 常用命令

```bash
# 构建镜像
docker build -t tfg_ui:latest -f Dockerfile .

# 运行容器
docker compose up -d

# 查看日志
docker compose logs -f

# 进入容器
docker exec -it tfg_ui bash

# 停止容器
docker compose down

# 重启容器
docker compose restart

# 查看容器状态
docker ps

# 查看镜像
docker images

# 清理未使用的资源
docker system prune -a
```

### 8.2 文件位置

| 文件 | 位置 | 说明 |
|-----|------|------|
| Dockerfile | `/root/TFG_ui/Dockerfile` | 主镜像构建文件 |
| Dockerfile.eval | `/root/TFG_ui/Dockerfile.eval` | 评测镜像构建文件 |
| docker-compose.yml | `/root/TFG_ui/docker-compose.yml` | Docker Compose 配置 |
| .dockerignore | `/root/TFG_ui/.dockerignore` | Docker 忽略文件配置 |
| 安装脚本 | `/root/TFG_ui/install_docker_china.sh` | Docker 一键安装脚本 |

### 8.3 时间估算

| 操作 | 时间 |
|-----|------|
| Docker 安装 | 10-20 分钟 |
| 首次构建镜像 | 30-60 分钟 |
| 代码修改后构建 | 5-15 分钟 |
| 依赖修改后构建 | 20-40 分钟 |

---

## 九、技术支持

如有问题，请查看：
- `项目运行环境说明.md`：环境配置详细说明
- `项目结构说明.md`：项目结构说明
- `TalkingGaussian/evaluation/评测流程说明.md`：评测流程详细说明
- GitHub Issues：提交问题反馈

---

## 十、总结

### ✅ 完整工作流程

1. **安装 Docker**（10-20 分钟）
2. **配置权限和镜像加速**（5 分钟）
3. **首次构建镜像**（30-60 分钟）
4. **运行容器测试**（1 分钟）
5. **修改代码后重新构建**（5-15 分钟）

### 📋 检查清单

- [ ] Docker 已安装并运行
- [ ] nvidia-docker2 已安装（GPU 支持）
- [ ] 用户权限已配置（可选）
- [ ] 镜像加速已配置（推荐）
- [ ] 镜像构建成功
- [ ] 容器运行正常
- [ ] 可以访问 http://localhost:5001

---


