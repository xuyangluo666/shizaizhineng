import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 检查用户是否存在
if not User.objects.filter(username='admin').exists():
    # 创建超级用户
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='password123'
    )
    print('超级用户创建成功！')
else:
    print('用户已存在！')
