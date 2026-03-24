import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 检查用户是否存在
print("检查用户列表:")
users = User.objects.all()
for user in users:
    print(f"用户名: {user.username}, 邮箱: {user.email}, 超级用户: {user.is_superuser}, 活跃: {user.is_active}")

# 尝试使用admin用户登录
from django.contrib.auth import authenticate

user = authenticate(username='admin', password='password123')
if user:
    print("\n登录成功!")
    print(f"用户: {user.username}, 活跃: {user.is_active}")
else:
    print("\n登录失败!")
