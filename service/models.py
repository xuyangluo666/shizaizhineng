from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings

class CustomUser(AbstractUser):
    """自定义用户模型"""
    email = models.EmailField(unique=True, verbose_name='邮箱')
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    activation_key = models.CharField(max_length=100, blank=True, verbose_name='激活码')
    key_expires = models.DateTimeField(null=True, blank=True, verbose_name='激活码过期时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户列表'
    
    def __str__(self):
        return self.username
    
    def send_activation_email(self):
        """发送激活邮件"""
        token = default_token_generator.make_token(self)
        uid = urlsafe_base64_encode(force_bytes(self.pk))
        activation_url = f"{settings.SITE_URL}/service/activate/{uid}/{token}/"
        
        subject = '账号激活'
        message = f'请点击以下链接激活您的账号：\n{activation_url}'
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>账号激活</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 20px;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>账号激活</h2>
                <p>亲爱的 {self.username}，</p>
                <p>感谢您注册实在智能KA客户服务管理系统！</p>
                <p>请点击下方按钮激活您的账号：</p>
                <a href="{activation_url}" class="button">激活账号</a>
                <p>如果按钮无法点击，请复制以下链接到浏览器打开：</p>
                <p>{activation_url}</p>
                <p>此链接将在7天后过期，请及时激活。</p>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email], html_message=html_message)
        
        self.activation_key = token
        self.key_expires = timezone.now() + timezone.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        self.save()
    
    def send_password_reset_email(self):
        """发送密码重置邮件"""
        token = default_token_generator.make_token(self)
        uid = urlsafe_base64_encode(force_bytes(self.pk))
        reset_url = f"{settings.SITE_URL}/service/reset-password/{uid}/{token}/"
        
        subject = '密码重置'
        message = f'请点击以下链接重置您的密码：\n{reset_url}'
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>密码重置</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 20px;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>密码重置</h2>
                <p>亲爱的 {self.username}，</p>
                <p>我们收到了您的密码重置请求。</p>
                <p>请点击下方按钮重置您的密码：</p>
                <a href="{reset_url}" class="button">重置密码</a>
                <p>如果按钮无法点击，请复制以下链接到浏览器打开：</p>
                <p>{reset_url}</p>
                <p>此链接将在一段时间后过期，请及时重置密码。</p>
                <p>如果您没有请求重置密码，请忽略此邮件。</p>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email], html_message=html_message)

# 客户类型常量
CUSTOMER_TYPE_TRIAL = 'trial'
CUSTOMER_TYPE_SELF_DEVELOP = 'self_develop'
CUSTOMER_TYPE_OPERATIONS = 'operations'

CUSTOMER_TYPE_CHOICES = [
    (CUSTOMER_TYPE_TRIAL, '试用客户'),
    (CUSTOMER_TYPE_SELF_DEVELOP, '自开发客户'),
    (CUSTOMER_TYPE_OPERATIONS, '售后运维客户'),
]

# 客户状态常量
CUSTOMER_STATUS_NORMAL = 'normal'
CUSTOMER_STATUS_ABNORMAL = 'abnormal'
CUSTOMER_STATUS_LOST = 'lost'

CUSTOMER_STATUS_CHOICES = [
    (CUSTOMER_STATUS_NORMAL, '正常'),
    (CUSTOMER_STATUS_ABNORMAL, '异常'),
    (CUSTOMER_STATUS_LOST, '流失'),
]

# 客户级别常量
CUSTOMER_LEVEL_A = 'A'
CUSTOMER_LEVEL_B = 'B'
CUSTOMER_LEVEL_C = 'C'

CUSTOMER_LEVEL_CHOICES = [
    (CUSTOMER_LEVEL_A, 'A'),
    (CUSTOMER_LEVEL_B, 'B'),
    (CUSTOMER_LEVEL_C, 'C'),
]

# 问题类型常量
PROBLEM_TYPE_PROCESS = 'process'
PROBLEM_TYPE_SOFTWARE = 'software'
PROBLEM_TYPE_INSTALL = 'install'
PROBLEM_TYPE_COMPLAINT = 'complaint'

PROBLEM_TYPE_CHOICES = [
    (PROBLEM_TYPE_PROCESS, '流程问题'),
    (PROBLEM_TYPE_SOFTWARE, '软件问题'),
    (PROBLEM_TYPE_INSTALL, '安装部署'),
    (PROBLEM_TYPE_COMPLAINT, '投诉'),
]

# 服务模式常量
SERVICE_MODE_REMOTE = 'remote'
SERVICE_MODE_ONSITE = 'onsite'

SERVICE_MODE_CHOICES = [
    (SERVICE_MODE_REMOTE, '远程'),
    (SERVICE_MODE_ONSITE, '现场'),
]

# 是否关单常量
IS_CLOSED_YES = 'yes'
IS_CLOSED_NO = 'no'

IS_CLOSED_CHOICES = [
    (IS_CLOSED_YES, '是'),
    (IS_CLOSED_NO, '否'),
]

# 项目状态常量
PROJECT_STATUS_ACTIVE = 'active'
PROJECT_STATUS_PAUSED = 'paused'
PROJECT_STATUS_ENDED = 'ended'

PROJECT_STATUS_CHOICES = [
    (PROJECT_STATUS_ACTIVE, '进行中'),
    (PROJECT_STATUS_PAUSED, '暂停'),
    (PROJECT_STATUS_ENDED, '结束'),
]

# 流程状态常量
PROCESS_STATUS_NORMAL = 'normal'
PROCESS_STATUS_ERROR = 'error'

PROCESS_STATUS_CHOICES = [
    (PROCESS_STATUS_NORMAL, '正常'),
    (PROCESS_STATUS_ERROR, '异常'),
]

# 流程部署环境常量
PROCESS_ENV_TEST = 'test'
PROCESS_ENV_PROD = 'prod'

PROCESS_ENV_CHOICES = [
    (PROCESS_ENV_TEST, '测试'),
    (PROCESS_ENV_PROD, '生产'),
]

class Customer(models.Model):
    """客户模型"""
    customer_id = models.CharField(max_length=50, unique=True, default='', verbose_name='客户id')
    name = models.CharField(max_length=255, unique=True, verbose_name='客户名称')
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        verbose_name='客户类型'
    )
    status = models.CharField(
        max_length=20,
        choices=CUSTOMER_STATUS_CHOICES,
        verbose_name='当前状态'
    )
    contact_person = models.CharField(max_length=100, verbose_name='负责人')
    sales_person = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_sales',
        verbose_name='销售负责人'
    )
    customer_level = models.CharField(
        max_length=1,
        choices=CUSTOMER_LEVEL_CHOICES,
        blank=True,
        verbose_name='客户级别'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='最近更新时间')
    
    class Meta:
        verbose_name = '客户'
        verbose_name_plural = '客户列表'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # 自动生成客户ID
        if not self.customer_id:
            # 生成五位数顺序编号，从00001开始
            try:
                # 获取所有客户ID
                customer_ids = Customer.objects.values_list('customer_id', flat=True)
                # 过滤出五位数数字格式的客户ID并转换为整数
                numeric_ids = []
                for cid in customer_ids:
                    try:
                        # 只考虑五位数的客户ID
                        if len(cid) == 5 and cid.isdigit():
                            numeric_ids.append(int(cid))
                    except (ValueError, TypeError):
                        pass
                # 找出最大的五位数客户ID
                if numeric_ids:
                    max_id = max(numeric_ids)
                    next_id = max_id + 1
                    # 确保不超过99999
                    if next_id > 99999:
                        raise ValueError('客户ID已达到最大值99999')
                else:
                    next_id = 1
                # 格式化为五位数，前导零
                self.customer_id = f'{next_id:05d}'
            except Exception as e:
                # 如果出现任何错误，使用默认值1
                self.customer_id = '00001'
                # 确保客户ID唯一
                while Customer.objects.filter(customer_id=self.customer_id).exists():
                    import random
                    self.customer_id = f'{random.randint(1, 99999):05d}'
        super().save(*args, **kwargs)

class CustomerTypeChangeLog(models.Model):
    """客户类型变更日志"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户')
    old_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, verbose_name='原类型')
    new_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, verbose_name='新类型')
    operator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='操作人')
    change_time = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    change_reason = models.TextField(verbose_name='变更原因')
    
    class Meta:
        verbose_name = '客户类型变更日志'
        verbose_name_plural = '客户类型变更日志'
    
    def __str__(self):
        return f"{self.customer.name} 类型变更: {self.get_old_type_display()} -> {self.get_new_type_display()}"

class Project(models.Model):
    """项目信息模型"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户')
    name = models.CharField(max_length=255, verbose_name='项目名称')
    contract_start_date = models.DateField(verbose_name='合同开始时间')
    contract_end_date = models.DateField(verbose_name='合同结束时间')
    project_manager = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='project_manager', verbose_name='项目负责人')
    technical_manager = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='technical_manager', verbose_name='技术负责人')
    status = models.CharField(
        max_length=20,
        choices=PROJECT_STATUS_CHOICES,
        default=PROJECT_STATUS_ACTIVE,
        verbose_name='项目状态'
    )
    description = models.TextField(blank=True, verbose_name='项目描述')
    
    class Meta:
        verbose_name = '项目信息'
        verbose_name_plural = '项目信息'
    
    def __str__(self):
        return self.name

class Process(models.Model):
    """流程列表模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    name = models.CharField(max_length=255, verbose_name='流程名称')
    description = models.TextField(blank=True, verbose_name='描述')
    deployment_environment = models.CharField(
        max_length=20,
        choices=PROCESS_ENV_CHOICES,
        verbose_name='部署环境'
    )
    status = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS_CHOICES,
        default=PROCESS_STATUS_NORMAL,
        verbose_name='状态'
    )
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '流程列表'
        verbose_name_plural = '流程列表'
    
    def __str__(self):
        return self.name

class Opportunity(models.Model):
    """商机编号模型 - 用于处理一个客户多个商机编号的关系"""
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='opportunities', 
        verbose_name='客户'
    )
    opportunity_number = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name='商机编号'
    )
    description = models.TextField(blank=True, verbose_name='详情')
    status = models.CharField(
        max_length=20,
        default='active',
        choices=[
            ('active', '有效'),
            ('inactive', '无效'),
            ('closed', '已关闭'),
        ],
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='最近更新时间')
    
    class Meta:
        verbose_name = '商机编号'
        verbose_name_plural = '商机编号列表'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['opportunity_number']),
        ]
    
    def __str__(self):
        return f"{self.customer.name} - {self.opportunity_number}"

class Problem(models.Model):
    """问题记录模型"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, null=True, blank=True, verbose_name='商机编号')
    title = models.CharField(max_length=255, verbose_name='问题标题')
    description = models.TextField(verbose_name='问题描述')
    problem_type = models.CharField(
        max_length=20,
        choices=PROBLEM_TYPE_CHOICES,
        default=PROBLEM_TYPE_PROCESS,
        verbose_name='问题类型'
    )
    service_mode = models.CharField(
        max_length=20,
        choices=SERVICE_MODE_CHOICES,
        default=SERVICE_MODE_REMOTE,
        verbose_name='服务模式'
    )
    handler = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='处理人')
    related_process = models.ForeignKey(Process, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联流程')
    is_closed = models.CharField(
        max_length=20,
        choices=IS_CLOSED_CHOICES,
        default=IS_CLOSED_NO,
        verbose_name='是否关单'
    )
    close_time = models.DateTimeField(null=True, blank=True, verbose_name='关单时间')
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '问题记录'
        verbose_name_plural = '问题记录'
    
    def __str__(self):
        return self.title

class TrialCustomer(models.Model):
    """试用客户扩展信息"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, verbose_name='客户')
    trial_start_time = models.DateTimeField(verbose_name='试用开始时间')
    trial_end_time = models.DateTimeField(verbose_name='试用到期时间')
    conversion_status = models.BooleanField(default=False, verbose_name='转化状态')
    
    class Meta:
        verbose_name = '试用客户信息'
        verbose_name_plural = '试用客户信息'
    
    def __str__(self):
        return f"{self.customer.name} 试用信息"

class File(models.Model):
    """文件管理模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    name = models.CharField(max_length=255, verbose_name='文件名称')
    file_type = models.CharField(max_length=50, verbose_name='类型')
    version = models.CharField(max_length=50, verbose_name='版本')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    uploader = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='上传人')
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    
    class Meta:
        verbose_name = '文件管理'
        verbose_name_plural = '文件管理'
    
    def __str__(self):
        return self.name

class OperationLog(models.Model):
    """操作日志模型"""
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='操作人')
    action = models.CharField(max_length=255, verbose_name='操作')
    object_type = models.CharField(max_length=100, verbose_name='操作对象类型')
    object_id = models.IntegerField(null=True, verbose_name='操作对象ID')
    ip_address = models.GenericIPAddressField(null=True, verbose_name='IP地址')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    details = models.TextField(blank=True, verbose_name='操作详情')
    
    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
    
    def __str__(self):
        return f"{self.user.username if self.user else '未知用户'} - {self.action}"
