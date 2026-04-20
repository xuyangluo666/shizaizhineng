from service.models import Customer
from django.db.models import Max

# 查看当前客户列表
print('Current customers:')
customers = Customer.objects.all()
for customer in customers:
    print(f'ID: {customer.id}, Customer ID: {customer.customer_id}, Name: {customer.name}')

# 查看最大客户ID
max_id = Customer.objects.aggregate(Max('customer_id'))['customer_id__max']
print(f'\nMax customer_id: {max_id}')

# 测试生成下一个客户ID
if max_id:
    try:
        next_id = int(max_id) + 1
        print(f'Next customer_id should be: {next_id:05d}')
    except (ValueError, TypeError):
        print('Error parsing max customer_id')
else:
    print('No customers yet, next customer_id should be: 00001')
