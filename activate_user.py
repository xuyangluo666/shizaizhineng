import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 激活admin用户
user = User.objects.get(username='admin')
user.is_active = True
user.save()

print(f"用户 {user.username} 已激活")
print(f"当前状态: 活跃={user.is_active}, 超级用户={user.is_superuser}")

# 尝试再次登录
from django.contrib.auth import authenticate

user = authenticate(username='admin', password='password123')
if user:
    print("\n登录成功!")
else:
    print("\n登录失败!")
