#!/bin/bash
set -e

echo "=========================================="
echo "Docker 和 NVIDIA Docker 安装脚本（使用国内镜像源）"
echo "=========================================="
echo "系统：Ubuntu 20.04"
echo "GPU：Tesla T4（驱动已安装）"
echo "=========================================="
echo ""

# 检查并修复代理配置（如果存在）
if [ -f /etc/apt/apt.conf.d/proxy.conf ]; then
    if grep -q "127.0.0.1:7890" /etc/apt/apt.conf.d/proxy.conf && ! grep -q "^#" /etc/apt/apt.conf.d/proxy.conf; then
        echo "[0/5] 检测到代理配置但代理服务未运行，正在注释..."
        sudo cp /etc/apt/apt.conf.d/proxy.conf /etc/apt/apt.conf.d/proxy.conf.backup
        sudo bash -c 'cat > /etc/apt/apt.conf.d/proxy.conf << EOF
# 代理配置已注释（代理服务未运行）
# Acquire::http::Proxy "http://127.0.0.1:7890";
# Acquire::https::Proxy "http://127.0.0.1:7890";
EOF'
        echo "代理配置已注释"
    fi
fi

# 删除备份文件（避免警告）
sudo rm -f /etc/apt/apt.conf.d/proxy.conf.backup

# 1. 安装 Docker（使用 Ubuntu 官方仓库的 docker.io，更稳定）
echo "[1/5] 安装 Docker（使用 Ubuntu 官方仓库）..."
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    docker.io \
    docker-compose

# 如果 docker.io 安装失败，尝试使用阿里云镜像
if ! command -v docker &> /dev/null; then
    echo ""
    echo "[1.5/5] docker.io 安装失败，尝试使用阿里云 Docker 镜像源..."
    
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# 2. 启动 Docker 服务
echo ""
echo "[2/5] 启动 Docker 服务..."
sudo systemctl start docker
sudo systemctl enable docker

# 3. 安装 NVIDIA Docker
echo ""
echo "[3/5] 安装 NVIDIA Docker..."
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# 尝试使用国内镜像源
if ! curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - 2>/dev/null; then
    echo "使用备用方法添加 NVIDIA Docker GPG 密钥..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
fi

# 添加仓库（使用官方源，如果失败会提示）
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2 || {
    echo "警告: nvidia-docker2 安装失败，尝试手动安装..."
    # 备用安装方法
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
}

# 4. 重启 Docker
echo ""
echo "[4/5] 重启 Docker 服务..."
sudo systemctl restart docker

# 5. 验证安装
echo ""
echo "[5/5] 验证安装..."
echo "Docker 版本："
docker --version || sudo docker --version
echo ""
echo "Docker Compose 版本："
docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo "Docker Compose 未找到"
echo ""

echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "测试 GPU 支持："
echo "  sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi"
echo ""
echo "将用户添加到 docker 组（推荐，避免每次使用 sudo）："
echo "  sudo usermod -aG docker \$USER"
echo "  newgrp docker"
echo ""

