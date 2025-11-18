from django.urls import path
from . import views

app_name = 'order'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('payment/<int:order_id>/', views.payment_process, name='payment_process'),
    path('created/<int:order_id>/', views.order_created, name='order_created'),
    path('ticket/<int:order_id>/', views.download_ticket, name='download_ticket'),
]