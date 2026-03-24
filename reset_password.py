import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 重置admin用户密码
user = User.objects.get(username='admin')
user.set_password('password123')  # 这会自动哈希密码
user.save()

print(f"用户 {user.username} 的密码已重置")

# 尝试再次登录
from django.contrib.auth import authenticate

user = authenticate(username='admin', password='password123')
if user:
    print("\n登录成功!")
else:
    print("\n登录失败!")

# 检查用户信息
user = User.objects.get(username='admin')
print(f"\n用户信息:")
print(f"用户名: {user.username}")
print(f"邮箱: {user.email}")
print(f"活跃: {user.is_active}")
print(f"超级用户: {user.is_superuser}")
print(f"密码哈希: {user.password}")
