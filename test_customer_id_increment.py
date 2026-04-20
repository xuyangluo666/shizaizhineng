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

# 测试创建多个客户，验证客户ID是否每次递增1
print('\nCreating test customers...')
for i in range(5):
    try:
        new_customer = Customer(
            name=f'Test Customer {i+1}',
            customer_type='trial',
            status='normal',
            contact_person=f'Test Person {i+1}'
        )
        new_customer.save()
        print(f'Created customer with ID: {new_customer.customer_id}')
    except Exception as e:
        print(f'Error creating customer: {e}')

# 查看创建后的客户列表
print('\nCustomers after creation:')
customers = Customer.objects.all()
for customer in customers:
    print(f'ID: {customer.id}, Customer ID: {customer.customer_id}, Name: {customer.name}')
