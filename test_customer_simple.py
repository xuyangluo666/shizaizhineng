#!/usr/bin/env python
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shizaizhineng.settings')
django.setup()

from service.models import Customer

# 查看当前客户列表
print('Current customers:')
customers = Customer.objects.all()
for customer in customers:
    print(f'ID: {customer.id}, Customer ID: {customer.customer_id}, Name: {customer.name}')

# 尝试创建一个新客户
try:
    new_customer = Customer(
        name='Test Customer',
        customer_type='trial',
        status='normal',
        contact_person='Test Person'
    )
    new_customer.save()
    print(f'\nNew customer created successfully with ID: {new_customer.customer_id}')
except Exception as e:
    print(f'\nError creating customer: {e}')
