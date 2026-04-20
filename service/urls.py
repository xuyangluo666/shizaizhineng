from django.urls import path
from . import views

app_name = 'service'

urlpatterns = [
    # 客户管理
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('customers/batch-delete/', views.CustomerBatchDeleteView.as_view(), name='customer_batch_delete'),
    path('customers/<int:pk>/change-type/', views.CustomerTypeChangeView.as_view(), name='customer_change_type'),
    # 客户导出导入
    path('customers/export/', views.CustomerExportView.as_view(), name='customer_export'),
    path('customers/import/', views.CustomerImportView.as_view(), name='customer_import'),
    
    # 问题记录管理
    path('customers/<int:customer_id>/problems/', views.ProblemListView.as_view(), name='problem_list'),
    path('problems/create/<int:customer_id>/', views.ProblemCreateView.as_view(), name='problem_create'),
    path('problems/<int:pk>/update/', views.ProblemUpdateView.as_view(), name='problem_update'),
    path('problems/<int:pk>/delete/', views.ProblemDeleteView.as_view(), name='problem_delete'),
    path('problems/batch-delete/', views.ProblemBatchDeleteView.as_view(), name='problem_batch_delete'),
    path('problems/import/<int:customer_id>/', views.ProblemImportView.as_view(), name='problem_import'),
    path('problems/export/', views.ProblemExportView.as_view(), name='problem_export'),
    
    # 项目管理
    path('projects/create/<int:customer_id>/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    
    # 文件管理
    path('projects/<int:project_id>/files/', views.FileListView.as_view(), name='file_list'),
    path('files/create/<int:project_id>/', views.FileCreateView.as_view(), name='file_create'),
    path('files/<int:pk>/delete/', views.FileDeleteView.as_view(), name='file_delete'),
    
    # 流程管理
    path('projects/<int:project_id>/processes/', views.ProcessListView.as_view(), name='process_list'),
    path('processes/create/<int:project_id>/', views.ProcessCreateView.as_view(), name='process_create'),
    path('processes/<int:pk>/update/', views.ProcessUpdateView.as_view(), name='process_update'),
    path('processes/<int:pk>/delete/', views.ProcessDeleteView.as_view(), name='process_delete'),
    # 获取客户流程
    path('customers/<int:customer_id>/processes/', views.CustomerProcessesView.as_view(), name='customer_processes'),
    path('customers/<int:customer_id>/opportunities/', views.CustomerOpportunitiesView.as_view(), name='customer_opportunities'),
    
    # 数据看板
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # 商机编号管理 API
    path('api/opportunities/add/', views.add_opportunity, name='add_opportunity'),
    path('api/opportunities/edit/', views.edit_opportunity, name='edit_opportunity'),
    path('api/opportunities/<int:opp_id>/delete/', views.delete_opportunity, name='delete_opportunity'),
    path('api/opportunities/<int:opp_id>/status/', views.update_opportunity_status, name='update_opportunity_status'),
    path('api/opportunities/customer/<int:customer_id>/', views.get_opportunities, name='get_opportunities'),
    
    # 商机编号管理视图
    path('opportunities/', views.OpportunityListView.as_view(), name='opportunity_list'),
    path('opportunities/export/', views.OpportunityExportView.as_view(), name='opportunity_export'),
    
    # 认证相关
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('activate/<uidb64>/<token>/', views.ActivateView.as_view(), name='activate'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('reset-password/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
