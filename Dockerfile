FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim

WORKDIR /app

# 使用阿里云Debian源（trixie版本）
RUN echo "deb http://mirrors.aliyun.com/debian trixie main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian trixie-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list && \
    # 确保不使用官方源
    echo "Acquire::http::Proxy \"DIRECT\";" > /etc/apt/apt.conf.d/99proxy && \
    echo "Acquire::https::Proxy \"DIRECT\";" >> /etc/apt/apt.conf.d/99proxy && \
    # 禁止使用官方源
    echo "Acquire::BlockForeignRepositories \"true\";" >> /etc/apt/apt.conf.d/99proxy

# 安装系统依赖并清理缓存
RUN apt-get update -y && \ 
    apt-get install -y --no-install-recommends \ 
    gcc \ 
    default-libmysqlclient-dev \ 
    pkg-config \ 
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 更换pip源为阿里云源并安装Python依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# 复制项目代码
COPY . .

# 创建静态文件目录
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

# 启动命令
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 --workers 3 shizaizhineng.wsgi:application"]
