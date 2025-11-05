from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
import os
import json

from .utils import require_admin, require_customer, SESSION_USER_ROLE, SESSION_USER_ID
from .models import UserAccount
from order.models import Order, OrderItem


def login_view(request: HttpRequest) -> HttpResponse:
    # Placeholder: vista de login no implementada aún
    return render(request, 'accounts/login.html')


def register_view(request: HttpRequest) -> HttpResponse:
    # Placeholder: vista de registro no implementada aún
    return render(request, 'accounts/register.html')


@require_admin
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    # Placeholder: panel admin-lite
    return render(request, 'accounts/admin/dashboard.html')


# --- Endpoints temporales de depuración ---
def debug_login_admin(request: HttpRequest) -> HttpResponse:
    """Fija en sesión el rol ADMIN para poder probar el admin-lite sin login."""
    # Seguridad: solo permitir en desarrollo + MockDB
    if not (getattr(settings, "DEBUG", False) and getattr(settings, "USE_MOCKDB", False)):
        return HttpResponseNotFound()
    request.session[SESSION_USER_ROLE] = UserAccount.ROLE_ADMIN
    # Opcional: asociar un id de usuario mock conocido (si existiera). No es requerido por ahora.
    request.session[SESSION_USER_ID] = 1
    return redirect(reverse('accounts:admin_products'))


def debug_login_customer(request: HttpRequest) -> HttpResponse:
    """Fija en sesión el rol CUSTOMER para poder probar funcionalidades de cliente sin login."""
    # Seguridad: solo permitir en desarrollo + MockDB
    if not (getattr(settings, "DEBUG", False) and getattr(settings, "USE_MOCKDB", False)):
        return HttpResponseNotFound()
    request.session[SESSION_USER_ROLE] = UserAccount.ROLE_CUSTOMER
    # Usar ID 1 para customer (ya que los pedidos de prueba están asignados a este ID)
    request.session[SESSION_USER_ID] = 5
    # Mostrar mensaje de éxito
    return HttpResponse(
        "Login como customer exitoso (ID=1). "
        "Ahora puedes probar la API en /accounts/api/orders/1/ (reemplaza el 1 con el ID del pedido que quieras ver)"
    )


def debug_logout(request: HttpRequest) -> HttpResponse:
    """Elimina claves de la sesión mock y redirige a login placeholder."""
    # Seguridad: solo permitir en desarrollo + MockDB
    if not (getattr(settings, "DEBUG", False) and getattr(settings, "USE_MOCKDB", False)):
        return HttpResponseNotFound()
    request.session.pop(SESSION_USER_ROLE, None)
    request.session.pop(SESSION_USER_ID, None)
    return redirect(reverse('accounts:login'))


@require_customer
def customer_order_detail(request: HttpRequest, order_id: int) -> HttpResponse:
    """Vista para que un customer consulte un pedido específico.
    
    Args:
        request: Solicitud HTTP
        order_id: ID del pedido a consultar
    
    Returns:
        JsonResponse con la información del pedido y sus items si existe y pertenece al customer.
        404 si el pedido no existe o no pertenece al customer actual.
    """
    # Obtener ID del usuario actual de la sesión
    user_id = request.session.get(SESSION_USER_ID)
    if not user_id:
        return HttpResponseNotFound()
    
    # En MockDB, asumimos que el ID del customer es el mismo que el del usuario
    customer_id = user_id
    
    # Buscar el pedido y verificar que pertenezca al customer
    # Si usamos MockDB, tomar la información directamente desde los JSON de tests/mockdb
    if getattr(settings, 'USE_MOCKDB', False):
        # Construir ruta al directorio tests/mockdb/data relativo a la raíz del repo
        repo_root = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(repo_root, 'tests', 'mockdb', 'data')
        orders_path = os.path.join(data_dir, 'orders.json')
        order_items_path = os.path.join(data_dir, 'order_items.json')
        products_path = os.path.join(data_dir, 'products.json')

        try:
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
        except Exception:
            return HttpResponseNotFound()

        order_obj = next((o for o in orders_data if int(o.get('id', 0)) == int(order_id)), None)
        if not order_obj:
            return HttpResponseNotFound()

        # Verificar que el pedido pertenezca al customer (en mockdb orders.json: customer is id)
        if int(order_obj.get('customer', 0)) != int(customer_id):
            return HttpResponseNotFound()

        # Cargar items y productos para enriquecer la respuesta si están disponibles
        items_list = []
        try:
            with open(order_items_path, 'r', encoding='utf-8') as f:
                order_items_data = json.load(f)
        except Exception:
            order_items_data = []

        try:
            with open(products_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception:
            products_data = []

        # Map productos por id
        products_map = {p.get('id'): p for p in products_data}

        for it in order_items_data:
            # Asociar items que referencien a este pedido (si existe campo 'order')
            if it.get('order') is None:
                # Si no hay referencia explícita, no lo incluimos
                continue
            if int(it.get('order')) != int(order_id):
                continue
            prod = products_map.get(it.get('product'))
            items_list.append({
                'product_name': prod.get('name') if prod else f"Producto {it.get('product')}",
                'quantity': int(it.get('quantity', 1)),
                'price': str(it.get('price', '0')),
                'size': it.get('size', ''),
                'total': str(float(it.get('price', 0)) * int(it.get('quantity', 1))),
            })

        payload = {
            'order': {
                'id': order_obj.get('id'),
                'order_number': order_obj.get('order_number'),
                'status': order_obj.get('status'),
                'total': order_obj.get('total'),
                'paid': order_obj.get('paid', False),
                'payment_method': order_obj.get('payment_method', ''),
            },
            'items': items_list,
        }
        return JsonResponse(payload)

    # Si no estamos en MockDB, usar ORM normal
    try:
        order = Order.objects.get(id=order_id)
        # Verificar que el pedido pertenezca al customer actual
        if not hasattr(order, 'customer') or getattr(order, 'customer', None) != customer_id:
            return HttpResponseNotFound()

        items = OrderItem.objects.filter(order=order)
        payload = {
            'order': {
                'id': order.id,
                'order_number': getattr(order, 'order_number', f'MOCK-{order.id:04d}'),
                'status': getattr(order, 'status', 'pending'),
                'total': str(getattr(order, 'total', 0)),
                'paid': getattr(order, 'paid', False),
                'payment_method': getattr(order, 'payment_method', ''),
            },
            'items': [{
                'product_name': getattr(item.product, 'name', 'Producto'),
                'quantity': getattr(item, 'quantity', 1),
                'price': str(getattr(item, 'price', 0)),
                'size': getattr(item, 'size', ''),
                'total': str(getattr(item, 'price', 0) * getattr(item, 'quantity', 1)),
            } for item in items]
        }
        return JsonResponse(payload)
    except Order.DoesNotExist:
        return HttpResponseNotFound()
