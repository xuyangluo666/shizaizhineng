import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from service.models import Problem

print("所有问题记录:")
for p in Problem.objects.all():
    print(f'ID: {p.id}, Title: {p.title}')

print(f"总共有 {Problem.objects.count()} 条问题记录")