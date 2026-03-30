#!/bin/bash

# 确保日志目录存在
mkdir -p /app/logs

# 确保日志文件存在
touch /app/logs/django.log

# 数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 启动应用
exec gunicorn --bind 0.0.0.0:8000 --workers 3 shizaizhineng.wsgi:application
