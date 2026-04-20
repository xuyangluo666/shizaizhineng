from django.contrib import admin
from .models import (
    CustomUser, Customer, CustomerTypeChangeLog, Problem, TrialCustomer,
    Project, File, Process, OperationLog
)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'status', 'contact_person', 'updated_at')
    list_filter = ('customer_type', 'status')
    search_fields = ('name', 'contact_person')

@admin.register(CustomerTypeChangeLog)
class CustomerTypeChangeLogAdmin(admin.ModelAdmin):
    list_display = ('customer', 'old_type', 'new_type', 'operator', 'change_time')
    list_filter = ('old_type', 'new_type')
    search_fields = ('customer__name', 'operator__username')

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'is_closed', 'handler')
    list_filter = ('is_closed', 'customer__customer_type')
    search_fields = ('title', 'description')

@admin.register(TrialCustomer)
class TrialCustomerAdmin(admin.ModelAdmin):
    list_display = ('customer', 'trial_start_time', 'trial_end_time', 'conversion_status')
    search_fields = ('customer__name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'project_manager', 'technical_manager', 'status')
    list_filter = ('status', 'customer')
    search_fields = ('name', 'description')

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'file_type', 'version', 'uploader', 'upload_time')
    list_filter = ('file_type', 'project')
    search_fields = ('name', 'version')

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'deployment_environment', 'status', 'update_time')
    list_filter = ('status', 'deployment_environment', 'project')
    search_fields = ('name', 'description')

@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'object_type', 'created_at', 'ip_address')
    list_filter = ('action', 'object_type')
    search_fields = ('user__username', 'action', 'details')

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
