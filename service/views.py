from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
import pandas as pd
import io
import os
from .models import (
    CustomUser, Customer, CustomerTypeChangeLog, Problem, TrialCustomer,
    Project, File, Process, OperationLog, Opportunity,
    CUSTOMER_TYPE_TRIAL, CUSTOMER_TYPE_SELF_DEVELOP, CUSTOMER_TYPE_OPERATIONS,
    CUSTOMER_STATUS_NORMAL, CUSTOMER_STATUS_ABNORMAL, CUSTOMER_STATUS_LOST,
    CUSTOMER_LEVEL_A, CUSTOMER_LEVEL_B, CUSTOMER_LEVEL_C,
    CUSTOMER_TYPE_CHOICES, CUSTOMER_STATUS_CHOICES, CUSTOMER_LEVEL_CHOICES
)

# 客户管理视图
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'service/customer_list.html'
    context_object_name = 'customers'
    
    def get_paginate_by(self, queryset):
        # 从请求中获取每页显示数量，默认为50
        paginate_by = self.request.GET.get('per_page', 50)
        try:
            paginate_by = int(paginate_by)
            # 确保每页数量在合理范围内
            if paginate_by < 1:
                paginate_by = 50
            elif paginate_by > 100:
                paginate_by = 100
        except (ValueError, TypeError):
            paginate_by = 50
        return paginate_by
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 搜索功能
        search_term = self.request.GET.get('search', '')
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)
        # 客户类型筛选
        customer_type = self.request.GET.get('type', '')
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加当前每页显示数量到上下文
        context['per_page'] = self.get_paginate_by(self.get_queryset())
        # 添加用户列表，用于处理人选择
        from .models import CustomUser
        context['users'] = CustomUser.objects.all()
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'service/customer_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        # 获取商机编号过滤参数
        opportunity_id = self.request.GET.get('opportunity')
        
        # 根据客户类型加载不同的模块
        if customer.customer_type == CUSTOMER_TYPE_OPERATIONS:
            # 运维客户显示项目、文件、流程、运维记录
            context['projects'] = Project.objects.filter(customer=customer)
            if opportunity_id:
                context['problems'] = Problem.objects.filter(customer=customer, opportunity_id=opportunity_id)
            else:
                context['problems'] = Problem.objects.filter(customer=customer)
        elif customer.customer_type == CUSTOMER_TYPE_SELF_DEVELOP:
            # 自开发客户显示问题记录和主要人员
            if opportunity_id:
                context['problems'] = Problem.objects.filter(customer=customer, opportunity_id=opportunity_id)
            else:
                context['problems'] = Problem.objects.filter(customer=customer)
        elif customer.customer_type == CUSTOMER_TYPE_TRIAL:
            # 试用客户显示试用问题记录和主要人员
            if opportunity_id:
                context['problems'] = Problem.objects.filter(customer=customer, opportunity_id=opportunity_id)
            else:
                context['problems'] = Problem.objects.filter(customer=customer)
            try:
                context['trial_info'] = TrialCustomer.objects.get(customer=customer)
            except TrialCustomer.DoesNotExist:
                context['trial_info'] = None
        # 添加用户列表，用于项目负责人和技术负责人选择
        context['users'] = CustomUser.objects.all()
        # 添加当前选中的商机编号
        context['selected_opportunity'] = opportunity_id
        return context

class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Customer
    template_name = 'service/customer_form.html'
    fields = ['name', 'customer_type', 'status', 'contact_person', 'opportunity_number', 'customer_level']
    success_url = reverse_lazy('service:customer_list')
    permission_required = 'service.add_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='创建客户',
                object_type='Customer',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建客户: {self.object.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='创建客户',
                object_type='Customer',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建客户: {self.object.name}'
            )
        # 如果是试用客户，创建试用信息
        if form.cleaned_data['customer_type'] == CUSTOMER_TYPE_TRIAL:
            TrialCustomer.objects.create(
                customer=self.object,
                trial_start_time=timezone.now(),
                trial_end_time=timezone.now() + timezone.timedelta(days=30),
                conversion_status=False
            )
        # 检查是否是AJAX请求
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '客户创建成功'})
        return response

class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Customer
    template_name = 'service/customer_form.html'
    fields = ['name', 'status', 'contact_person', 'opportunity_number', 'customer_level']
    success_url = reverse_lazy('service:customer_list')
    permission_required = 'service.change_customer'
    
    def handle_no_permission(self):
        from django.http import HttpResponseForbidden
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        if customer.customer_type == CUSTOMER_TYPE_TRIAL:
            try:
                context['trial_info'] = TrialCustomer.objects.get(customer=customer)
            except TrialCustomer.DoesNotExist:
                context['trial_info'] = None
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='更新客户',
                object_type='Customer',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新客户: {self.object.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='更新客户',
                object_type='Customer',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新客户: {self.object.name}'
            )
        # 处理试用客户信息
        if self.object.customer_type == CUSTOMER_TYPE_TRIAL:
            trial_start_time = self.request.POST.get('trial_start_time')
            trial_end_time = self.request.POST.get('trial_end_time')
            conversion_status = self.request.POST.get('conversion_status') == 'on'
            
            try:
                trial_customer = TrialCustomer.objects.get(customer=self.object)
                if trial_start_time:
                    trial_customer.trial_start_time = trial_start_time
                if trial_end_time:
                    trial_customer.trial_end_time = trial_end_time
                trial_customer.conversion_status = conversion_status
                trial_customer.save()
            except TrialCustomer.DoesNotExist:
                # 如果不存在，创建新的试用信息
                if trial_start_time and trial_end_time:
                    TrialCustomer.objects.create(
                        customer=self.object,
                        trial_start_time=trial_start_time,
                        trial_end_time=trial_end_time,
                        conversion_status=conversion_status
                    )
        # 检查是否是AJAX请求
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '客户信息更新成功'})
        return response

class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Customer
    template_name = 'service/customer_confirm_delete.html'
    success_url = reverse_lazy('service:customer_list')
    permission_required = 'service.delete_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='删除客户',
                object_type='Customer',
                object_id=customer.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除客户: {customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='删除客户',
                object_type='Customer',
                object_id=customer.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除客户: {customer.name}'
            )
        return super().delete(request, *args, **kwargs)

class CustomerBatchDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'service.delete_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def post(self, request):
        customer_ids = request.POST.getlist('customer_ids[]')
        if customer_ids:
            customers = Customer.objects.filter(id__in=customer_ids)
            # 记录操作日志
            for customer in customers:
                try:
                    OperationLog.objects.create(
                        user=request.user,
                        action='批量删除客户',
                        object_type='Customer',
                        object_id=customer.id,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details=f'批量删除客户: {customer.name}'
                    )
                except Exception as e:
                    # 如果外键约束失败，尝试不设置user字段
                    OperationLog.objects.create(
                        user=None,
                        action='批量删除客户',
                        object_type='Customer',
                        object_id=customer.id,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details=f'批量删除客户: {customer.name}'
                    )
            delete_count = customers.count()
            customers.delete()
            if delete_count == 1:
                return JsonResponse({'success': True, 'message': '成功删除1个客户'})
            else:
                return JsonResponse({'success': True, 'message': f'成功删除{delete_count}个客户'})
        return JsonResponse({'success': False, 'message': '请选择要删除的客户'})

class CustomerTypeChangeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'service/customer_type_change.html'
    permission_required = 'service.change_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        # 确定合法的目标类型
        valid_target_types = []
        if customer.customer_type == CUSTOMER_TYPE_TRIAL:
            valid_target_types = [CUSTOMER_TYPE_SELF_DEVELOP, CUSTOMER_TYPE_OPERATIONS]
        elif customer.customer_type == CUSTOMER_TYPE_SELF_DEVELOP:
            valid_target_types = [CUSTOMER_TYPE_OPERATIONS]
        # 售后运维客户不可变更类型
        elif customer.customer_type == CUSTOMER_TYPE_OPERATIONS:
            valid_target_types = []
        
        context = {
            'customer': customer,
            'valid_target_types': valid_target_types
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        old_type = customer.customer_type
        new_type = request.POST.get('new_type')
        change_reason = request.POST.get('change_reason')
        init_project = request.POST.get('init_project') == 'on'
        
        # 验证类型变更的合法性
        valid = False
        if old_type == CUSTOMER_TYPE_TRIAL:
            if new_type in [CUSTOMER_TYPE_SELF_DEVELOP, CUSTOMER_TYPE_OPERATIONS]:
                valid = True
        elif old_type == CUSTOMER_TYPE_SELF_DEVELOP:
            if new_type == CUSTOMER_TYPE_OPERATIONS:
                valid = True
        
        if not valid:
            return redirect('service:customer_detail', pk=pk)
        
        # 记录类型变更日志
        try:
            CustomerTypeChangeLog.objects.create(
                customer=customer,
                old_type=old_type,
                new_type=new_type,
                operator=request.user,
                change_reason=change_reason
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置operator字段
            CustomerTypeChangeLog.objects.create(
                customer=customer,
                old_type=old_type,
                new_type=new_type,
                operator=None,
                change_reason=change_reason
            )
        
        # 更新客户类型
        customer.customer_type = new_type
        # 更新客户状态
        if new_type == CUSTOMER_TYPE_OPERATIONS:
            customer.status = CUSTOMER_STATUS_NORMAL
        elif new_type == CUSTOMER_TYPE_SELF_DEVELOP:
            customer.status = CUSTOMER_STATUS_NORMAL
        customer.save()
        
        # 如果变更为运维客户且需要初始化项目
        if new_type == CUSTOMER_TYPE_OPERATIONS and init_project:
            Project.objects.create(
                customer=customer,
                name=f'{customer.name} 默认项目',
                contract_start_date=timezone.now().date(),
                contract_end_date=timezone.now().date() + timezone.timedelta(days=365),
                project_manager=request.user,
                status='active'
            )
        
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='变更客户类型',
                object_type='Customer',
                object_id=customer.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'客户类型变更: {customer.name} 从 {old_type} 变更为 {new_type}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='变更客户类型',
                object_type='Customer',
                object_id=customer.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'客户类型变更: {customer.name} 从 {old_type} 变更为 {new_type}'
            )
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '客户类型变更成功'})
        return redirect('service:customer_detail', pk=pk)

# 问题记录管理视图
class ProblemListView(LoginRequiredMixin, ListView):
    model = Problem
    template_name = 'service/problem_list.html'
    context_object_name = 'problems'
    paginate_by = 10
    
    def get_queryset(self):
        customer_id = self.kwargs.get('customer_id')
        queryset = Problem.objects.filter(customer_id=customer_id)
        
        # 筛选功能
        related_process = self.request.GET.get('related_process', '')
        is_closed = self.request.GET.get('is_closed', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        opportunity = self.request.GET.get('opportunity', '')
        
        if related_process:
            queryset = queryset.filter(related_process_id=related_process)
        if is_closed:
            queryset = queryset.filter(is_closed=is_closed)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        if opportunity:
            queryset = queryset.filter(opportunity_id=opportunity)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_id'] = self.kwargs.get('customer_id')
        # 获取客户信息
        customer = get_object_or_404(Customer, id=self.kwargs.get('customer_id'))
        context['customer'] = customer
        # 获取客户的商机编号
        context['opportunities'] = customer.opportunities.all()
        # 获取可选的流程（仅运维客户）
        if customer.customer_type == CUSTOMER_TYPE_OPERATIONS:
            projects = Project.objects.filter(customer=customer)
            context['processes'] = Process.objects.filter(project__in=projects)
        # 获取所有用户（用于处理人选择）
        from .models import CustomUser
        context['users'] = CustomUser.objects.all()
        return context

class ProblemCreateView(LoginRequiredMixin, CreateView):
    model = Problem
    template_name = 'service/problem_form.html'
    fields = ['opportunity', 'title', 'description', 'problem_type', 'service_mode', 'handler', 'related_process', 'is_closed', 'close_time']
    
    def get_success_url(self):
        return reverse('service:problem_list', kwargs={'customer_id': self.kwargs.get('customer_id')})
    
    def get_initial(self):
        initial = super().get_initial()
        return initial
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)
    
    def form_valid(self, form):
        customer_id = self.kwargs.get('customer_id')
        form.instance.customer = get_object_or_404(Customer, id=customer_id)
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='创建问题记录',
                object_type='Problem',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建问题: {self.object.title} 客户: {self.object.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='创建问题记录',
                object_type='Problem',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建问题: {self.object.title} 客户: {self.object.customer.name}'
            )
        # 检查是否是AJAX请求
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '问题记录创建成功'})
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_id'] = self.kwargs.get('customer_id')
        # 获取可选的流程（仅运维客户）
        customer = get_object_or_404(Customer, id=self.kwargs.get('customer_id'))
        context['customer'] = customer
        # 获取客户的商机编号
        context['opportunities'] = customer.opportunities.all()
        if customer.customer_type == CUSTOMER_TYPE_OPERATIONS:
            projects = Project.objects.filter(customer=customer)
            context['processes'] = Process.objects.filter(project__in=projects)
        return context

class ProblemUpdateView(LoginRequiredMixin, UpdateView):
    model = Problem
    template_name = 'service/problem_form.html'
    fields = ['opportunity', 'title', 'description', 'problem_type', 'service_mode', 'handler', 'related_process', 'is_closed', 'close_time']
    
    def get_success_url(self):
        return reverse('service:problem_list', kwargs={'customer_id': self.object.customer.id})
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='更新问题记录',
                object_type='Problem',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新问题: {self.object.title} 客户: {self.object.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='更新问题记录',
                object_type='Problem',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新问题: {self.object.title} 客户: {self.object.customer.name}'
            )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取可选的流程（仅运维客户）
        if self.object.customer.customer_type == CUSTOMER_TYPE_OPERATIONS:
            projects = Project.objects.filter(customer=self.object.customer)
            context['processes'] = Process.objects.filter(project__in=projects)
        # 添加customer_id和customer到上下文
        context['customer_id'] = self.object.customer.id
        context['customer'] = self.object.customer
        # 获取客户的商机编号
        context['opportunities'] = self.object.customer.opportunities.all()
        return context

class ProblemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Problem
    template_name = 'service/problem_confirm_delete.html'
    permission_required = 'service.delete_problem'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get_success_url(self):
        return reverse('service:problem_list', kwargs={'customer_id': self.object.customer.id})
    
    def delete(self, request, *args, **kwargs):
        problem = self.get_object()
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='删除问题记录',
                object_type='Problem',
                object_id=problem.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除问题: {problem.title} 客户: {problem.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='删除问题记录',
                object_type='Problem',
                object_id=problem.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除问题: {problem.title} 客户: {problem.customer.name}'
            )
        return super().delete(request, *args, **kwargs)

class ProblemBatchDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'service.delete_problem'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def post(self, request):
        problem_ids = request.POST.getlist('problem_ids')
        if problem_ids:
            problems = Problem.objects.filter(id__in=problem_ids)
            # 记录操作日志
            for problem in problems:
                try:
                    OperationLog.objects.create(
                        user=request.user,
                        action='批量删除问题记录',
                        object_type='Problem',
                        object_id=problem.id,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details=f'批量删除问题: {problem.title} 客户: {problem.customer.name}'
                    )
                except Exception as e:
                    # 如果外键约束失败，尝试不设置user字段
                    OperationLog.objects.create(
                        user=None,
                        action='批量删除问题记录',
                        object_type='Problem',
                        object_id=problem.id,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details=f'批量删除问题: {problem.title} 客户: {problem.customer.name}'
                    )
            delete_count = problems.count()
            problems.delete()
            if delete_count == 1:
                return JsonResponse({'success': True, 'message': '成功删除1个问题'})
            else:
                return JsonResponse({'success': True, 'message': f'成功删除{delete_count}个问题'})
        return JsonResponse({'success': False, 'message': '请选择要删除的问题'})

class ProblemImportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'service/problem_import.html'
    permission_required = 'service.add_problem'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request, customer_id):
        # 检查是否是模板下载请求
        if request.GET.get('action') == 'download_template':
            customer = get_object_or_404(Customer, id=customer_id)
            if customer.customer_type == 'operations':
                template_path = 'service/templates/service/operation_import_template.xlsx'
                filename = '运维记录导入模板.xlsx'
            else:
                template_path = 'service/templates/service/problem_import_template.xlsx'
                filename = '问题记录导入模板.xlsx'
            
            try:
                with open(template_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response
            except FileNotFoundError:
                return JsonResponse({'success': False, 'message': '模板文件不存在'})
        
        return render(request, self.template_name, {'customer_id': customer_id})
    
    def post(self, request, customer_id):
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '请选择文件'})
        
        file = request.FILES['file']
        try:
            # 获取文件扩展名
            file_name = file.name
            file_extension = file_name.split('.')[-1].lower()
            
            # 读取文件
            try:
                # 先检查文件前几个字节，判断是否为有效的Excel文件
                file_content = file.read(1024)
                file.seek(0)  # 重置文件指针
                
                # 检查是否为有效的Excel文件
                if file_extension in ['xlsx', 'xls']:
                    # 尝试使用不同的引擎读取文件，以兼容不同格式的Excel文件
                    engines = ['openpyxl', 'xlrd']
                    df = None
                    
                    for engine in engines:
                        try:
                            file.seek(0)  # 重置文件指针
                            df = pd.read_excel(file, engine=engine)
                            break  # 成功读取，跳出循环
                        except Exception as e:
                            continue  # 尝试下一个引擎
                    
                    # 如果所有引擎都失败，尝试使用默认引擎
                    if df is None:
                        try:
                            file.seek(0)
                            df = pd.read_excel(file)
                        except Exception as e:
                            # 所有尝试都失败，返回错误
                            return JsonResponse({'success': False, 'message': f'读取文件失败: {str(e)}。请确保文件格式正确且未损坏。'})
                elif file_extension in ['csv']:
                    # 读取CSV文件，尝试不同的编码
                    encodings = ['utf-8-sig', 'gbk', 'gb18030', 'utf-16']
                    df = None
                    
                    for encoding in encodings:
                        try:
                            file.seek(0)  # 重置文件指针
                            df = pd.read_csv(file, encoding=encoding)
                            break  # 成功读取��跳出循环
                        except Exception as e:
                            continue  # 尝试下一个编码
                    
                    # 如果所有编码都失败，返回错误
                    if df is None:
                        return JsonResponse({'success': False, 'message': '读取CSV文件失败，无法识别编码格式。请确保文件格式正确且未损坏。'})
                else:
                    return JsonResponse({'success': False, 'message': '不支持的文件格式，请上传.xlsx、.xls或.csv文件'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'读取文件失败: {str(e)}。请确保文件格式正确且未损坏。'})
            # 处理数据
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    customer_name = row.get('客户名称')
                    title = row.get('问题标题') or row.get('运维标题')
                    description = row.get('问题描述')
                    occurrence_time = row.get('出现时间')
                    status = row.get('状态')
                    problem_reason = row.get('问题原因')
                    reason_type = row.get('原因分类')
                    solution = row.get('解决方案')
                    solve_time = row.get('解决时间')
                    handler_name = row.get('处理人')
                    related_process_name = row.get('关联流程')
                    
                    # 验证必填字段
                    if not customer_name or not title or not description:
                        error_count += 1
                        errors.append(f'第{index+2}行: 缺少必填字段')
                        continue
                    
                    # 查找客户
                    try:
                        customer = Customer.objects.get(name=customer_name)
                    except Customer.DoesNotExist:
                        error_count += 1
                        errors.append(f'第{index+2}行: 客户不存在')
                        continue
                    
                    # 处理运维记录的必填字段
                    if customer.customer_type == 'operations':
                        if not related_process_name:
                            error_count += 1
                            errors.append(f'第{index+2}行: 运维记录的关联流程为必填字段')
                            continue
                    
                    # 创建问题记录
                    problem = Problem(
                        customer=customer,
                        title=title,
                        description=description,
                        status=status if status else 'pending',
                        problem_reason=problem_reason if problem_reason else '',
                        solution=solution if solution else ''
                    )
                    
                    # 处理出现时间
                    if occurrence_time:
                        try:
                            problem.occurrence_time = pd.to_datetime(occurrence_time)
                        except:
                            pass
                    
                    # 处理原因分类
                    if reason_type:
                        problem.reason_type = reason_type
                    
                    # 处理解决时间
                    if solve_time:
                        try:
                            problem.solve_time = pd.to_datetime(solve_time)
                        except:
                            pass
                    
                    # 处理处理人
                    if handler_name:
                        try:
                            handler = CustomUser.objects.get(username=handler_name)
                            problem.handler = handler
                        except CustomUser.DoesNotExist:
                            pass
                    

                    
                    # 处理关联流程
                    if related_process_name and customer.customer_type == 'operations':
                        try:
                            # 查找该客户下的所有项目
                            projects = Project.objects.filter(customer=customer)
                            # 查找关联流程
                            for project in projects:
                                try:
                                    process = Process.objects.get(project=project, name=related_process_name)
                                    problem.related_process = process
                                    break
                                except Process.DoesNotExist:
                                    continue
                            if not problem.related_process:
                                error_count += 1
                                errors.append(f'第{index+2}行: 关联流程不存在')
                                continue
                        except Exception as e:
                            error_count += 1
                            errors.append(f'第{index+2}行: 关联流程处理失败: {str(e)}')
                            continue
                    
                    problem.save()
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f'第{index+2}行: {str(e)}')
            
            # 记录操作日志
            try:
                OperationLog.objects.create(
                    user=request.user,
                    action='导入问题记录',
                    object_type='Problem',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'导入问题记录: 成功 {success_count} 条, 失败 {error_count} 条'
                )
            except Exception as e:
                # 如果外键约束失败，尝试不设置user字段
                OperationLog.objects.create(
                    user=None,
                    action='导入问题记录',
                    object_type='Problem',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'导入问题记录: 成功 {success_count} 条, 失败 {error_count} 条'
                )
            
            return JsonResponse({
                'success': True,
                'message': f'导入完成，成功 {success_count} 条, 失败 {error_count} 条',
                'errors': errors,
                'redirect_url': reverse('service:problem_list', kwargs={'customer_id': customer_id})
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'导入失败: {str(e)}'})

class ProblemExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'service.view_problem'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request):
        # 获取筛选参数
        customer_id = request.GET.get('customer_id')
        status = request.GET.get('status')
        
        # 构建查询集
        queryset = Problem.objects.all()
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if status:
            queryset = queryset.filter(status=status)
        
        # 准备导出数据
        data = []
        for problem in queryset:
            # 基础字段
            row = {
                '客户名称': problem.customer.name,
                '问题标题': problem.title,
                '问题描述': problem.description,
                '出现时间': problem.occurrence_time.strftime('%Y-%m-%d %H:%M:%S') if problem.occurrence_time else '',
                '状态': dict(Problem._meta.get_field('status').choices).get(problem.status, problem.status),
                '问题原因': problem.problem_reason,
                '原因分类': dict(Problem._meta.get_field('reason_type').choices).get(problem.reason_type, problem.reason_type),
                '解决方案': problem.solution,
                '解决时间': problem.solve_time.strftime('%Y-%m-%d %H:%M:%S') if problem.solve_time else '',
                '处理人': problem.handler.username if problem.handler else ''
            }
            
            # 运维记录特有字段
            if problem.customer.customer_type == 'operations':
                row['关联流程'] = problem.related_process.name if problem.related_process else ''
            
            data.append(row)
        
        # 创建Excel文件
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='问题记录')
        output.seek(0)
        
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='导出问题记录',
                object_type='Problem',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'导出问题记录: {len(data)} 条'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='导出问题记录',
                object_type='Problem',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'导出问题记录: {len(data)} 条'
            )
        
        # 返回响应
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=problems_{timezone.now().strftime("%Y%m%d%H%M%S")}.xlsx'
        return response

# 项目管理视图
class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'service/project_form.html'
    fields = ['name', 'contract_start_date', 'contract_end_date', 'project_manager', 'technical_manager', 'status']
    
    def get_success_url(self):
        return reverse('service:customer_detail', kwargs={'pk': self.kwargs.get('customer_id')})
    
    def form_valid(self, form):
        customer_id = self.kwargs.get('customer_id')
        form.instance.customer = get_object_or_404(Customer, id=customer_id)
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='创建项目',
                object_type='Project',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建项目: {self.object.name} 客户: {self.object.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='创建项目',
                object_type='Project',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建项目: {self.object.name} 客户: {self.object.customer.name}'
            )
        # 检查是否是AJAX请求
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '项目创建成功'})
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_id'] = self.kwargs.get('customer_id')
        # 添加用户列表，用于项目负责人和技术负责人选择
        from .models import CustomUser
        context['users'] = CustomUser.objects.all()
        return context

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = 'service/project_form.html'
    fields = ['name', 'contract_start_date', 'contract_end_date', 'project_manager', 'technical_manager', 'status', 'description']
    
    def get_success_url(self):
        return reverse('service:customer_detail', kwargs={'pk': self.object.customer.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_id'] = self.object.customer.id
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='更新项目',
                object_type='Project',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新项目: {self.object.name} 客户: {self.object.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='更新项目',
                object_type='Project',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新项目: {self.object.name} 客户: {self.object.customer.name}'
            )
        return response

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'service/project_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('service:customer_detail', kwargs={'pk': self.object.customer.id})
    
    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='删除项目',
                object_type='Project',
                object_id=project.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除项目: {project.name} 客户: {project.customer.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='删除项目',
                object_type='Project',
                object_id=project.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除项目: {project.name} 客户: {project.customer.name}'
            )
        response = super().delete(request, *args, **kwargs)
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '项目删除成功'})
        return response

# 文件管理视图
class FileListView(LoginRequiredMixin, ListView):
    model = File
    template_name = 'service/file_list.html'
    context_object_name = 'files'
    paginate_by = 10
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return File.objects.filter(project_id=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project_id'] = project_id
        context['project'] = get_object_or_404(Project, id=project_id)
        # 添加客户列表和用户列表，用于记录快捷新增
        from .models import Customer, CustomUser
        context['customers'] = Customer.objects.all()
        context['users'] = CustomUser.objects.all()
        return context

class FileCreateView(LoginRequiredMixin, CreateView):
    model = File
    template_name = 'service/file_form.html'
    fields = []  # 不使用表单字段，所有数据从上传文件自动提取
    
    def get_success_url(self):
        return reverse('service:file_list', kwargs={'project_id': self.kwargs.get('project_id')})
    
    def form_valid(self, form):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        form.instance.project = project
        
        # 尝试设置上传者，处理外键约束错误
        try:
            form.instance.uploader = self.request.user
        except Exception as e:
            form.instance.uploader = None
        
        # 处理文件上传
        if 'file' in self.request.FILES:
            file = self.request.FILES['file']
            
            # 检查文件是否已存在
            existing_file = File.objects.filter(project=project, name=file.name).first()
            if existing_file:
                form.add_error(None, f'文件 "{file.name}" 已存在于该项目中')
                return self.form_invalid(form)
            
            # 自动提取文件信息
            form.instance.name = file.name
            form.instance.file_type = file.name.split('.')[-1] if '.' in file.name else '未知'
            form.instance.version = '1.0.0'  # 默认版本
            
            # 创建上传目录
            upload_dir = os.path.join('uploads', f'project_{project_id}')
            os.makedirs(upload_dir, exist_ok=True)
            # 保存文件
            file_path = os.path.join(upload_dir, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            # 存储文件路径
            form.instance.file_path = file_path
        
        try:
            response = super().form_valid(form)
            # 记录操作日志
            try:
                OperationLog.objects.create(
                    user=self.request.user,
                    action='上传文件',
                    object_type='File',
                    object_id=self.object.id,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details=f'上传文件: {self.object.name} 项目: {self.object.project.name}'
                )
            except Exception as e:
                # 如果外键约束失败，尝试不设置user字段
                OperationLog.objects.create(
                    user=None,
                    action='上传文件',
                    object_type='File',
                    object_id=self.object.id,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details=f'上传文件: {self.object.name} 项目: {self.object.project.name}'
                )
            return response
        except Exception as e:
            # 如果保存文件时出现外键约束错误，尝试不设置uploader
            form.instance.uploader = None
            response = super().form_valid(form)
            # 记录操作日志
            try:
                OperationLog.objects.create(
                    user=self.request.user,
                    action='上传文件',
                    object_type='File',
                    object_id=self.object.id,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details=f'上传文件: {self.object.name} 项目: {self.object.project.name}'
                )
            except Exception as e:
                # 如果外键约束失败，尝试不设置user字段
                OperationLog.objects.create(
                    user=None,
                    action='上传文件',
                    object_type='File',
                    object_id=self.object.id,
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    details=f'上传文件: {self.object.name} 项目: {self.object.project.name}'
                )
            return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_id'] = self.kwargs.get('project_id')
        return context

class FileDeleteView(LoginRequiredMixin, DeleteView):
    model = File
    template_name = 'service/file_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('service:file_list', kwargs={'project_id': self.object.project.id})
    
    def delete(self, request, *args, **kwargs):
        file = self.get_object()
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='删除文件',
                object_type='File',
                object_id=file.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除文件: {file.name} 项目: {file.project.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='删除文件',
                object_type='File',
                object_id=file.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除文件: {file.name} 项目: {file.project.name}'
            )
        return super().delete(request, *args, **kwargs)

# 流程管理视图
class ProcessListView(LoginRequiredMixin, ListView):
    model = Process
    template_name = 'service/process_list.html'
    context_object_name = 'processes'
    paginate_by = 10
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return Process.objects.filter(project_id=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project_id'] = project_id
        context['project'] = get_object_or_404(Project, id=project_id)
        # 添加客户列表和用户列表，用于记录快捷新增
        from .models import Customer, CustomUser
        context['customers'] = Customer.objects.all()
        context['users'] = CustomUser.objects.all()
        return context

class ProcessCreateView(LoginRequiredMixin, CreateView):
    model = Process
    template_name = 'service/process_form.html'
    fields = ['name', 'description', 'deployment_environment', 'status']
    
    def get_success_url(self):
        return reverse('service:process_list', kwargs={'project_id': self.kwargs.get('project_id')})
    
    def form_valid(self, form):
        project_id = self.kwargs.get('project_id')
        form.instance.project = get_object_or_404(Project, id=project_id)
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='创建流程',
                object_type='Process',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建流程: {self.object.name} 项目: {self.object.project.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='创建流程',
                object_type='Process',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'创建流程: {self.object.name} 项目: {self.object.project.name}'
            )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_id'] = self.kwargs.get('project_id')
        return context

class ProcessUpdateView(LoginRequiredMixin, UpdateView):
    model = Process
    template_name = 'service/process_form.html'
    fields = ['name', 'description', 'deployment_environment', 'status']
    
    def get_success_url(self):
        return reverse('service:process_list', kwargs={'project_id': self.object.project.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_id'] = self.object.project.id
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=self.request.user,
                action='更新流程',
                object_type='Process',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新流程: {self.object.name} 项目: {self.object.project.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='更新流程',
                object_type='Process',
                object_id=self.object.id,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                details=f'更新流程: {self.object.name} 项目: {self.object.project.name}'
            )
        return response

class ProcessDeleteView(LoginRequiredMixin, DeleteView):
    model = Process
    template_name = 'service/process_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('service:process_list', kwargs={'project_id': self.object.project.id})
    
    def delete(self, request, *args, **kwargs):
        process = self.get_object()
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='删除流程',
                object_type='Process',
                object_id=process.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除流程: {process.name} 项目: {process.project.name}'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='删除流程',
                object_type='Process',
                object_id=process.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'删除流程: {process.name} 项目: {process.project.name}'
            )
        return super().delete(request, *args, **kwargs)

# 获取客户流程的视图
class CustomerProcessesView(LoginRequiredMixin, View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        # 获取客户的所有项目
        projects = Project.objects.filter(customer=customer)
        # 获取所有项目的流程
        processes = Process.objects.filter(project__in=projects)
        # 构建流程列表
        process_list = []
        for process in processes:
            process_list.append({
                'id': process.id,
                'name': f'{process.project.name} - {process.name}'
            })
        return JsonResponse({'processes': process_list})

# 获取客户商机编号的视图
class CustomerOpportunitiesView(LoginRequiredMixin, View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        # 获取客户的所有商机编号
        opportunities = customer.opportunities.all()
        # 构建商机编号列表
        opportunity_list = []
        for opportunity in opportunities:
            opportunity_list.append({
                'id': opportunity.id,
                'opportunity_number': opportunity.opportunity_number
            })
        return JsonResponse({'opportunities': opportunity_list})

# 数据看板视图
class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'service/dashboard.html'
    permission_required = 'service.view_dashboard'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request):
        # 客户类型分布
        customer_type_distribution = Customer.objects.values('customer_type').annotate(count=Count('id'))
        
        # 客户状态分布
        customer_status_distribution = Customer.objects.values('status').annotate(count=Count('id'))
        
        # 问题状态分布
        problem_status_distribution = Problem.objects.values('is_closed').annotate(count=Count('id'))
        
        # 问题类型分布
        problem_type_distribution = Problem.objects.values('problem_type').annotate(count=Count('id'))
        
        # 服务模式分布
        service_mode_distribution = Problem.objects.values('service_mode').annotate(count=Count('id'))
        
        # 客户级别分布
        customer_level_distribution = Customer.objects.values('customer_level').annotate(count=Count('id'))
        
        # 运维项目统计
        project_count = Project.objects.count()
        active_projects = Project.objects.filter(status='active').count()
        
        # 商机编号统计
        opportunity_count = Opportunity.objects.count()
        
        # 问题趋势（最近30天）
        start_date = timezone.now() - timezone.timedelta(days=30)
        problem_trend = Problem.objects.filter(created_at__gte=start_date)\
            .extra(select={'date': 'DATE(created_at)'})\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
        
        # 最近7天的问题趋势
        start_date_7 = timezone.now() - timezone.timedelta(days=7)
        problem_trend_7 = Problem.objects.filter(created_at__gte=start_date_7)\
            .extra(select={'date': 'DATE(created_at)'})\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
        
        # 添加客户列表和用户列表，用于记录快捷新增
        from .models import CustomUser
        context = {
            'customer_type_distribution': customer_type_distribution,
            'customer_status_distribution': customer_status_distribution,
            'problem_status_distribution': problem_status_distribution,
            'problem_type_distribution': problem_type_distribution,
            'service_mode_distribution': service_mode_distribution,
            'customer_level_distribution': customer_level_distribution,
            'project_count': project_count,
            'active_projects': active_projects,
            'opportunity_count': opportunity_count,
            'problem_trend': problem_trend,
            'problem_trend_7': problem_trend_7,
            'customers': Customer.objects.all(),
            'users': CustomUser.objects.all()
        }
        return render(request, self.template_name, context)

# 客户导出视图
class CustomerExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'service.view_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request):
        # 获取所有客户
        customers = Customer.objects.all()
        
        # 准备导出数据
        data = []
        for customer in customers:
            row = {
                '客户ID': customer.customer_id,
                '客户名称': customer.name,
                '客户类型': dict(CUSTOMER_TYPE_CHOICES).get(customer.customer_type, customer.customer_type),
                '当前状态': dict(CUSTOMER_STATUS_CHOICES).get(customer.status, customer.status),
                '负责人': customer.contact_person,
                '商机编号': customer.opportunity_number or '',
                '客户级别': dict(CUSTOMER_LEVEL_CHOICES).get(customer.customer_level, customer.customer_level) or '',
                '创建时间': customer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '最近更新时间': customer.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            data.append(row)
        
        # 创建Excel文件
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='客户数据')
        output.seek(0)
        
        # 记录操作日志
        try:
            OperationLog.objects.create(
                user=request.user,
                action='导出客户数据',
                object_type='Customer',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'导出客户数据: {len(data)} 条'
            )
        except Exception as e:
            # 如果外键约束失败，尝试不设置user字段
            OperationLog.objects.create(
                user=None,
                action='导出客户数据',
                object_type='Customer',
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f'导出客户数据: {len(data)} 条'
            )
        
        # 返回响应
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=customers_{timezone.now().strftime("%Y%m%d%H%M%S")}.xlsx'
        return response

# 客户导入视图
class CustomerImportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'service/customer_import.html'
    permission_required = 'service.add_customer'
    
    def handle_no_permission(self):
        from django.shortcuts import render
        return render(self.request, 'service/permission_denied.html', status=403)
    
    def get(self, request):
        # 检查是否是模板下载请求
        if request.GET.get('action') == 'download_template':
            template_path = 'service/templates/service/customer_import_template.csv'
            filename = '客户导入模板.csv'
            
            try:
                with open(template_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response
            except FileNotFoundError:
                return JsonResponse({'success': False, 'message': '模板文件不存在'})
        
        return render(request, self.template_name)
    
    def post(self, request):
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '请选择文件'})
        
        file = request.FILES['file']
        try:
            # 获取文件扩展名
            file_name = file.name
            file_extension = file_name.split('.')[-1].lower()
            
            # 读取文件
            try:
                # 尝试使用pandas直接读取，让它自动处理格式和编码
                file.seek(0)  # 重置文件指针
                
                if file_extension in ['xlsx', 'xls']:
                    # 读取Excel文件
                    df = pd.read_excel(file)
                elif file_extension in ['csv']:
                    # 读取CSV文件，使用更简单的方法
                    df = pd.read_csv(file)
                else:
                    return JsonResponse({'success': False, 'message': '不支持的文件格式，请上传.xlsx、.xls或.csv文件'})
            except Exception as e:
                # 如果直接读取失败，尝试使用更通用的方法
                try:
                    file.seek(0)  # 重置文件指针
                    # 尝试使用不同的方式读取
                    if file_extension in ['csv']:
                        # 尝试使用Python内置的csv模块
                        import csv
                        from io import StringIO
                        
                        # 读取文件内容
                        content = file.read()
                        
                        # 尝试不同的编码
                        encodings = ['utf-8-sig', 'gbk', 'gb18030']
                        decoded_content = None
                        
                        for encoding in encodings:
                            try:
                                decoded_content = content.decode(encoding)
                                break
                            except Exception:
                                continue
                        
                        if decoded_content:
                            # 使用csv模块读取
                            reader = csv.reader(StringIO(decoded_content))
                            rows = list(reader)
                            
                            if rows:
                                # 构建DataFrame
                                headers = rows[0]
                                data = rows[1:]
                                df = pd.DataFrame(data, columns=headers)
                            else:
                                return JsonResponse({'success': False, 'message': '文件内容为空，请确保文件格式正确且未损坏。'})
                        else:
                            return JsonResponse({'success': False, 'message': '无法识别文件编码格式，请确保文件格式正确且未损坏。'})
                    else:
                        # 对于Excel文件，返回更详细的错误信息
                        return JsonResponse({'success': False, 'message': f'读取文件失败: {str(e)}。请确保文件是有效的Excel文件且未损坏。'})
                except Exception as e2:
                    return JsonResponse({'success': False, 'message': f'读取文件失败: {str(e2)}。请确保文件格式正确且未损坏。'})
            
            # 处理数据
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # 获取数据
                    customer_id = row.get('客户ID', '').strip() if pd.notna(row.get('客户ID')) else ''
                    name = row.get('客户名称', '').strip() if pd.notna(row.get('客户名称')) else ''
                    customer_type = row.get('客户类型', '').strip() if pd.notna(row.get('客户类型')) else ''
                    status = row.get('当前状态', '').strip() if pd.notna(row.get('当前状态')) else ''
                    contact_person = row.get('负责人', '').strip() if pd.notna(row.get('负责人')) else ''
                    opportunity_number = row.get('商机编号', '').strip() if pd.notna(row.get('商机编号')) else ''
                    customer_level = row.get('客户级别', '').strip() if pd.notna(row.get('客户级别')) else ''
                    
                    # 验证必填字段
                    if not name or not customer_type or not status or not contact_person:
                        error_count += 1
                        errors.append(f'第{index+2}行: 缺少必填字段')
                        continue
                    
                    # 转换客户类型
                    type_mapping = {'试用客户': CUSTOMER_TYPE_TRIAL, '自开发客户': CUSTOMER_TYPE_SELF_DEVELOP, '售后运维客户': CUSTOMER_TYPE_OPERATIONS}
                    if customer_type not in type_mapping:
                        error_count += 1
                        errors.append(f'第{index+2}行: 客户类型无效')
                        continue
                    customer_type = type_mapping[customer_type]
                    
                    # 转换客户状态
                    status_mapping = {'正常': CUSTOMER_STATUS_NORMAL, '异常': CUSTOMER_STATUS_ABNORMAL, '流失': CUSTOMER_STATUS_LOST}
                    if status not in status_mapping:
                        error_count += 1
                        errors.append(f'第{index+2}行: 客户状态无效')
                        continue
                    status = status_mapping[status]
                    
                    # 转换客户级别
                    if customer_level:
                        level_mapping = {'A': CUSTOMER_LEVEL_A, 'B': CUSTOMER_LEVEL_B, 'C': CUSTOMER_LEVEL_C}
                        if customer_level not in level_mapping:
                            error_count += 1
                            errors.append(f'第{index+2}行: 客户级别无效')
                            continue
                        customer_level = level_mapping[customer_level]
                    
                    # 检查客户ID是否已存在
                    if customer_id:
                        if Customer.objects.filter(customer_id=customer_id).exists():
                            error_count += 1
                            errors.append(f'第{index+2}行: 客户ID已存在')
                            continue
                    
                    # 检查客户名称是否已存在
                    if Customer.objects.filter(name=name).exists():
                        error_count += 1
                        errors.append(f'第{index+2}行: 客户名称已存在')
                        continue
                    
                    # 创建客户
                    customer = Customer(
                        customer_id=customer_id,
                        name=name,
                        customer_type=customer_type,
                        status=status,
                        contact_person=contact_person,
                        opportunity_number=opportunity_number,
                        customer_level=customer_level
                    )
                    customer.save()
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f'第{index+2}行: {str(e)}')
            
            # 记录操作日志
            try:
                OperationLog.objects.create(
                    user=request.user,
                    action='导入客户数据',
                    object_type='Customer',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'导入客户数据: 成功 {success_count} 条, 失败 {error_count} 条'
                )
            except Exception as e:
                # 如果外键约束失败，尝试不设置user字段
                OperationLog.objects.create(
                    user=None,
                    action='导入客户数据',
                    object_type='Customer',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'导入客户数据: 成功 {success_count} 条, 失败 {error_count} 条'
                )
            
            return JsonResponse({
                'success': True,
                'message': f'导入完成，成功 {success_count} 条, 失败 {error_count} 条',
                'errors': errors,
                'redirect_url': reverse('service:customer_list')
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'导入失败: {str(e)}'})

# 认证相关视图
class RegisterView(FormView):
    template_name = 'service/register.html'
    success_url = reverse_lazy('service:login')
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # 验证密码
        if password1 != password2:
            messages.error(request, '两次密码输入不一致')
            return redirect('service:register')
        
        # 验证用户是否已存在
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return redirect('service:register')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, '邮箱已被注册')
            return redirect('service:register')
        
        # 创建用户
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password1,
            is_active=False
        )
        
        # 发送激活邮件
        user.send_activation_email()
        messages.success(request, '注册成功，请查看邮箱激活账号')
        return redirect('service:login')

class ActivateView(View):
    template_name = 'service/activate.html'
    
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            return render(request, self.template_name, {'uidb64': uidb64, 'token': token})
        else:
            messages.error(request, '激活链接无效或已过期')
            return redirect('service:login')
    
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.activation_key = ''
            user.key_expires = None
            user.save()
            messages.success(request, '账号激活成功，请登录')
            return redirect('service:login')
        else:
            messages.error(request, '激活链接无效或已过期')
            return redirect('service:login')

class LoginView(FormView):
    template_name = 'service/login.html'
    success_url = reverse_lazy('service:customer_list')
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('service:customer_list')
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        resend_email = request.POST.get('resend_email')
        
        # 检查是否请求重新发送激活邮件
        if resend_email:
            try:
                user = CustomUser.objects.get(username=username)
                if not user.is_active:
                    user.send_activation_email()
                    messages.success(request, '激活邮件已重新发送，请查看邮箱')
                else:
                    messages.error(request, '账号已激活，请直接登录')
            except CustomUser.DoesNotExist:
                messages.error(request, '用户名不存在')
            return redirect('service:login')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('service:customer_list')
            else:
                messages.error(request, '账号未激活，请查看邮箱激活')
                return redirect('service:login')
        else:
            # 检查是否存在该用户名且未激活的用户
            try:
                user = CustomUser.objects.get(username=username)
                if not user.is_active:
                    messages.error(request, '账号未激活，是否重新发送激活邮件？')
                    return render(request, self.template_name, {'username': username, 'not_activated': True})
            except CustomUser.DoesNotExist:
                pass
            messages.error(request, '用户名或密码错误')
            return redirect('service:login')

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('service:login')

class PasswordResetView(FormView):
    template_name = 'service/password_reset.html'
    success_url = reverse_lazy('service:login')
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        try:
            user = CustomUser.objects.get(username=username, email=email)
            user.send_password_reset_email()
            messages.success(request, '密码重置邮件已发送，请查看邮箱')
        except CustomUser.DoesNotExist:
            messages.error(request, '用户名和邮箱不匹配')
        
        return redirect('service:login')

class PasswordResetConfirmView(FormView):
    template_name = 'service/password_reset_confirm.html'
    success_url = reverse_lazy('service:login')
    
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            return render(request, self.template_name, {'uidb64': uidb64, 'token': token})
        else:
            messages.error(request, '重置链接无效或已过期')
            return redirect('service:login')
    
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            if password1 != password2:
                messages.error(request, '两次密码输入不一致')
                return redirect('service:password_reset_confirm', uidb64=uidb64, token=token)
            
            user.set_password(password1)
            user.save()
            messages.success(request, '密码重置成功，请登录')
            return redirect('service:login')
        else:
            messages.error(request, '重置链接无效或已过期')
            return redirect('service:login')

# 根路径重定向视图
def root_redirect(request):
    """根路径重定向，未登录跳转到登录页，已登录跳转到客户列表页"""
    if request.user.is_authenticated:
        return redirect('service:customer_list')
    else:
        return redirect('service:login')


# ===== 商机编号 API 视图 =====
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import json

@require_http_methods(["POST"])
@csrf_protect
def add_opportunity(request):
    """
    API: 添加商机编号
    POST 请求体：
    {
        "customer_id": 1,
        "opportunity_number": "OPP001",
        "description": "商机详情"
    }
    """
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        opportunity_number = data.get('opportunity_number', '').strip()
        description = data.get('description', '').strip()
        
        if not customer_id or not opportunity_number:
            return JsonResponse({
                'success': False, 
                'message': '客户ID和商机编号不能为空'
            }, status=400)
        
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': '客户不存在'
            }, status=404)
        
        # 检查是否已存在相同的商机编号（全局唯一性）
        if Opportunity.objects.filter(opportunity_number=opportunity_number).exists():
            return JsonResponse({
                'success': False, 
                'message': f'商机编号 {opportunity_number} 已存在'
            }, status=400)
        
        opp = Opportunity.objects.create(
            customer=customer,
            opportunity_number=opportunity_number,
            description=description,
            status='active'
        )
        
        return JsonResponse({
            'success': True, 
            'message': '添加成功',
            'data': {
                'id': opp.id,
                'opportunity_number': opp.opportunity_number,
                'description': opp.description,
                'status': opp.status
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@require_http_methods(["DELETE"])
@csrf_protect
def delete_opportunity(request, opp_id):
    """
    API: 删除商机编号
    DELETE /service/api/opportunities/{id}/delete/
    """
    try:
        opp = Opportunity.objects.get(id=opp_id)
        opp.delete()
        return JsonResponse({
            'success': True, 
            'message': '删除成功'
        })
    except Opportunity.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': '商机编号不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_opportunities(request, customer_id):
    """
    API: 获取客户的所有商机编号
    GET /service/api/opportunities/customer/{customer_id}/
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        opportunities = customer.opportunities.all().order_by('-created_at')
        
        data = [{
            'id': opp.id,
            'opportunity_number': opp.opportunity_number,
            'description': opp.description,
            'status': opp.status,
            'created_at': opp.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for opp in opportunities]
        
        return JsonResponse({
            'success': True, 
            'data': data,
            'count': len(data)
        })
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': '客户不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@require_http_methods(["PUT"])
@csrf_protect
def update_opportunity_status(request, opp_id):
    """
    API: 更新商机编号状态
    PUT /service/api/opportunities/{id}/status/
    请求体：
    {
        "status": "active" | "inactive" | "closed"
    }
    """
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        valid_statuses = ['active', 'inactive', 'closed']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False, 
                'message': f'无效的状态，必须是以下之一: {", ".join(valid_statuses)}'
            }, status=400)
        
        opp = Opportunity.objects.get(id=opp_id)
        opp.status = new_status
        opp.save()
        
        return JsonResponse({
            'success': True, 
            'message': '状态更新成功',
            'data': {
                'id': opp.id,
                'status': opp.status
            }
        })
    except Opportunity.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': '商机编号不存在'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_protect
def edit_opportunity(request):
    """
    API: 编辑商机编号
    POST 请求体：
    {
        "id": 1,
        "customer_id": 1,
        "opportunity_number": "OPP002",
        "description": "商机详情"
    }
    """
    try:
        data = json.loads(request.body)
        opp_id = data.get('id')
        opportunity_number = data.get('opportunity_number', '').strip()
        description = data.get('description', '').strip()
        
        if not opp_id or not opportunity_number:
            return JsonResponse({
                'success': False, 
                'message': '商机编号 ID 和商机编号不能为空'
            }, status=400)
        
        try:
            opp = Opportunity.objects.get(id=opp_id)
        except Opportunity.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': '商机编号不存在'
            }, status=404)
        
        # 检查新商机编号是否已被其他商机使用
        if Opportunity.objects.filter(opportunity_number=opportunity_number).exclude(id=opp_id).exists():
            return JsonResponse({
                'success': False, 
                'message': f'商机编号 {opportunity_number} 已存在'
            }, status=400)
        
        opp.opportunity_number = opportunity_number
        opp.description = description
        opp.save()
        
        return JsonResponse({
            'success': True, 
            'message': '编辑成功',
            'data': {
                'id': opp.id,
                'opportunity_number': opp.opportunity_number,
                'description': opp.description,
                'status': opp.status
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': '无效的 JSON 数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }, status=500)


class OpportunityListView(LoginRequiredMixin, ListView):
    """商机编号列表视图"""
    model = Opportunity
    template_name = 'service/opportunity_list.html'
    context_object_name = 'opportunities'
    paginate_by = 50
    
    def get_paginate_by(self, queryset):
        # 从请求中获取每页显示数量，默认为50
        paginate_by = self.request.GET.get('per_page', 50)
        try:
            paginate_by = int(paginate_by)
            # 确保每页数量在合理范围内
            if paginate_by < 1:
                paginate_by = 50
            elif paginate_by > 100:
                paginate_by = 100
        except (ValueError, TypeError):
            paginate_by = 50
        return paginate_by
    
    def get_queryset(self):
        queryset = Opportunity.objects.all().select_related('customer').order_by('-created_at')
        
        # 搜索功能 - 搜索商机编号或客户名称
        search_term = self.request.GET.get('search', '')
        if search_term:
            queryset = queryset.filter(
                Q(opportunity_number__icontains=search_term) |
                Q(customer__name__icontains=search_term)
            )
        
        # 按状态筛选
        status_filter = self.request.GET.get('status', '')
        if status_filter in ['active', 'inactive', 'closed']:
            queryset = queryset.filter(status=status_filter)
        
        # 按客户筛选
        customer_id = self.request.GET.get('customer_id', '')
        if customer_id:
            try:
                queryset = queryset.filter(customer_id=int(customer_id))
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加当前每页显示数量到上下文
        context['per_page'] = self.get_paginate_by(self.get_queryset())
        # 添加客户列表，用于筛选
        context['customers'] = Customer.objects.all().order_by('name')
        # 添加当前筛选值
        context['search_term'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['customer_filter'] = self.request.GET.get('customer_id', '')
        # 统计数据
        all_opportunities = Opportunity.objects.all()
        context['stats'] = {
            'total': all_opportunities.count(),
            'active': all_opportunities.filter(status='active').count(),
            'inactive': all_opportunities.filter(status='inactive').count(),
            'closed': all_opportunities.filter(status='closed').count(),
        }
        return context


class OpportunityExportView(LoginRequiredMixin, View):
    """商机编号导出视图"""
    
    def get(self, request):
        # 构建查询集
        queryset = Opportunity.objects.all().select_related('customer').order_by('-created_at')
        
        # 应用筛选条件
        search_term = request.GET.get('search', '')
        if search_term:
            queryset = queryset.filter(
                Q(opportunity_number__icontains=search_term) |
                Q(customer__name__icontains=search_term)
            )
        
        status_filter = request.GET.get('status', '')
        if status_filter in ['active', 'inactive', 'closed']:
            queryset = queryset.filter(status=status_filter)
        
        customer_id = request.GET.get('customer_id', '')
        if customer_id:
            try:
                queryset = queryset.filter(customer_id=int(customer_id))
            except (ValueError, TypeError):
                pass
        
        # 创建 DataFrame
        data = []
        status_map = {'active': '有效', 'inactive': '无效', 'closed': '已关闭'}
        
        for opp in queryset:
            data.append({
                '商机编号': opp.opportunity_number,
                '客户名称': opp.customer.name,
                '客户ID': opp.customer.customer_id,
                '状态': status_map.get(opp.status, opp.status),
                '创建时间': opp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '更新时间': opp.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        df = pd.DataFrame(data)
        
        # 创建 Excel 文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='商机编号')
        output.seek(0)
        
        # 返回文件
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="opportunities.xlsx"'
        return response
