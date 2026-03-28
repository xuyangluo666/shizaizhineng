FROM m.daocloud.io/docker.io/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 配置 Debian 源为阿里云，并安装系统依赖（合并层）
RUN rm -rf /etc/apt/sources.list.d/* /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian trixie-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .

# 使用阿里云 PyPI 源安装 Python 依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# 复制项目代码
COPY . .

# 创建静态文件目录和日志目录并设置权限
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

EXPOSE 8000

# 启动脚本（需要创建 entrypoint.sh 并赋予执行权限）
COPY --chmod=0755 entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]