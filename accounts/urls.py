from django.urls import path
from django.conf import settings
from . import views
from . import admin_views


app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('admin-lite/', views.admin_dashboard, name='admin_dashboard'),
    # Productos (admin-lite)
    path('admin-lite/products/', admin_views.product_list, name='admin_products'),
    path('admin-lite/products/new/', admin_views.product_create, name='admin_product_create'),
    path('admin-lite/products/<int:id>/edit/', admin_views.product_edit, name='admin_product_edit'),
    path('admin-lite/products/<int:id>/delete/', admin_views.product_delete, name='admin_product_delete'),
    # Clientes (admin-lite)
    path('admin-lite/customers/', admin_views.customer_list, name='admin_customers'),
    path('admin-lite/customers/new/', admin_views.customer_create, name='admin_customer_create'),
    path('admin-lite/customers/<int:id>/edit/', admin_views.customer_edit, name='admin_customer_edit'),
    path('admin-lite/customers/<int:id>/delete/', admin_views.customer_delete, name='admin_customer_delete'),
        # Checkout (solo pruebas, admin-lite)
        path('admin-lite/checkout/delivery/', admin_views.checkout_delivery, name='admin_checkout_delivery'),
        path('admin-lite/checkout/payment/', admin_views.checkout_payment, name='admin_checkout_payment'),
    # Ventas y pedidos (admin-lite)
    path('admin-lite/sales/', admin_views.sales_dashboard, name='admin_sales_dashboard'),
    path('admin-lite/orders/', admin_views.order_list, name='admin_orders'),
    path('admin-lite/orders/<int:id>/', admin_views.order_detail, name='admin_order_detail'),
    path('admin-lite/orders/<int:id>/status/', admin_views.order_update_status, name='admin_order_update_status'),
]

# Endpoints de depuración SOLO disponibles en desarrollo y con MockDB
if settings.DEBUG and getattr(settings, "USE_MOCKDB", False):
    urlpatterns += [
        path('debug/login-admin/', views.debug_login_admin, name='debug_login_admin'),
        path('debug/logout/', views.debug_logout, name='debug_logout'),
    ]
