from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

import os
import json
from pathlib import Path

from .utils import require_admin, require_customer, SESSION_USER_ROLE, SESSION_USER_ID
from .models import UserAccount
from order.models import Order, OrderItem

@csrf_exempt
def update_field(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=400)

    try:
        data = json.loads(request.body)
        field = data["field"]
        value = data["value"]
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)

    user = request.session.get("mock_user")
    if not user:
        return JsonResponse({"status": "error", "message": "No autenticado"}, status=403)

    json_path = (
        Path(__file__).resolve().parent.parent
        / "tests" / "mockdb" / "data" / "customers.json"
    )

    with open(json_path, "r", encoding="utf-8") as file:
        users = json.load(file)

    for u in users:
        if u.get("email") == user.get("email"):
            u[field] = value
            break
    else:
        return JsonResponse({"status": "error", "message": "Usuario no encontrado"}, status=404)


    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4, ensure_ascii=False)

    user[field] = value
    request.session["mock_user"] = user

    return JsonResponse({"status": "ok"})

def login_view(request):
    """Login view that supports both customers and admins"""
    # Guest order lookup
    guest_orders = []
    search_order_number = None
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Paths to data files
        base_path = Path(__file__).resolve().parent.parent / 'tests' / 'mockdb' / 'data'
        data_path_customers = base_path / 'customers.json'
        data_path_admin = base_path / 'admin.json'

        all_users = []
        
        # Load customers
        try:
            with open(data_path_customers, 'r', encoding='utf-8') as file:
                customers = json.load(file)
                # Ensure customers have role
                for customer in customers:
                    if 'role' not in customer:
                        customer['role'] = 'customer'
                all_users.extend(customers)
                print(f"[LOGIN] Loaded {len(customers)} customers")
        except FileNotFoundError:
            print("[LOGIN] customers.json not found")
            pass
        except Exception as e:
            print(f"[LOGIN] Error loading customers: {e}")
        
        # Load admins
        try:
            with open(data_path_admin, 'r', encoding='utf-8') as file:
                admins = json.load(file)
                # Ensure admins have role
                for admin in admins:
                    if 'role' not in admin:
                        admin['role'] = 'admin'
                all_users.extend(admins)
                print(f"[LOGIN] Loaded {len(admins)} admins")
        except FileNotFoundError:
            print("[LOGIN] admin.json not found")
            pass
        except Exception as e:
            print(f"[LOGIN] Error loading admins: {e}")

        if not all_users:
            messages.error(request, 'No se encontró el archivo de usuarios.')
            return render(request, 'accounts/login.html')
        
        # Check credentials
        user_found = None
        for user in all_users:
            user_email = user.get('email', '').strip()
            user_password = str(user.get('password', '')).strip()
            
            print(f"[LOGIN] Checking user: {user_email} (role: {user.get('role')})")
            
            if user_email == email and user_password == password:
                user_found = user
                print(f"[LOGIN] Match found! User: {user_email}, Role: {user.get('role')}")
                break
        
        if user_found:
            # Set session data
            request.session['mock_user'] = user_found
            request.session['mock_user_role'] = user_found.get('role', 'customer')
            request.session['mock_user_id'] = user_found.get('id')
            
            # Redirect based on role
            if user_found.get('role') == 'admin':
                messages.success(request, f'Bienvenido Admin: {user_found.get("first_name", "")} {user_found.get("last_name", "")}')
                print(f"[LOGIN] Admin login successful, redirecting to dashboard")
                return redirect('accounts:admin_dashboard')
            else:
                messages.success(request, f'Bienvenido: {user_found.get("first_name", "")} {user_found.get("last_name", "")}')
                print(f"[LOGIN] Customer login successful")
                return redirect('shop:product_list')
        else:
            print(f"[LOGIN] No match found for email: {email}")
            messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    
    # Handle guest order lookup (GET request)
    elif request.method == 'GET' and request.GET.get('order_number'):
        search_order_number = request.GET.get('order_number').strip()
        
        if getattr(settings, 'USE_MOCKDB', False):
            repo_root = os.path.dirname(os.path.dirname(__file__))
            data_dir = os.path.join(repo_root, 'tests', 'mockdb', 'data')
            orders_path = os.path.join(data_dir, 'orders.json')
            order_items_path = os.path.join(data_dir, 'order_items.json')
            products_path = os.path.join(data_dir, 'products.json')

            try:
                with open(orders_path, 'r', encoding='utf-8') as f:
                    orders_data = json.load(f)
                
                with open(order_items_path, 'r', encoding='utf-8') as f:
                    order_items_data = json.load(f)
                
                with open(products_path, 'r', encoding='utf-8') as f:
                    products_data = json.load(f)
                
                found_order = next(
                    (o for o in orders_data if o.get('order_number', '').upper() == search_order_number.upper()),
                    None
                )
                
                if found_order:
                    products_map = {p.get('id'): p for p in products_data}
                    order_id = found_order.get('id')
                    items = [
                        {
                            'product_name': products_map.get(item.get('product'), {}).get('name', 'Producto'),
                            'quantity': item.get('quantity', 1),
                            'price': item.get('price', 0),
                            'size': item.get('size', ''),
                        }
                        for item in order_items_data
                        if item.get('order') == order_id
                    ]
                    found_order['items'] = items
                    guest_orders.append(found_order)
                
            except Exception as e:
                print(f"Error al cargar pedido: {e}")

    return render(request, 'accounts/login.html', {
        'guest_orders': guest_orders,
        'search_order_number': search_order_number
    })

def profile_view(request):
    if 'mock_user' in request.session:
        return render(request, 'accounts/profile.html', {'user': request.session['mock_user']})

    else:
        return redirect('accounts:login')

def logout_view(request):
    if 'mock_user' in request.session:
        del request.session['mock_user']
    
    if 'mock_user_role' in request.session:
        del request.session['mock_user_role']
    
    if 'mock_user_id' in request.session:
        del request.session['mock_user_id']
    
    request.session.flush()
    
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('accounts:login')


def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        city = request.POST.get('city', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validaciones básicas
        if not all([first_name, last_name, email, address, postal_code, city, phone_number, password1, password2]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'accounts/register.html')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'accounts/register.html')

        # Cargar usuarios existentes
        data_path = Path(__file__).resolve().parent.parent / 'tests' / 'mockdb' / 'data' / 'customers.json'

        try:
            with open(data_path, 'r', encoding='utf-8') as file:
                users = json.load(file)
        except FileNotFoundError:
            users = []

        # Verificar si el email ya existe
        for user in users:
            if user.get('email') == email:
                messages.error(request, 'El email ya está registrado.')
                return render(request, 'accounts/register.html')

        # Generar nuevo ID (máximo ID + 1)
        new_id = max([user.get('id', 0) for user in users], default=0) + 1

        # Crear nuevo usuario
        new_user = {
            'id': new_id,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone_number,
            'address': address,
            'city': city,
            'postal_code': postal_code,
            'password': password1
        }

        users.append(new_user)

        # Guardar en el JSON
        try:
            with open(data_path, 'w', encoding='utf-8') as file:
                json.dump(users, file, indent=4, ensure_ascii=False)
            
            # Iniciar sesión automáticamente
            request.session['mock_user'] = new_user
            return redirect('shop:product_list')
        except Exception as e:
            messages.error(request, f'Error al guardar el usuario: {str(e)}')
            return render(request, 'accounts/register.html')

    return render(request, 'accounts/register.html')

def my_data_view(request):
    if 'mock_user' not in request.session:
        return redirect('accounts:login')

    user = request.session['mock_user']

    return render(request, 'accounts/my_data.html', {'user': user})


def my_orders_view(request):
    """Vista para mostrar los pedidos del usuario logueado."""
    if 'mock_user' not in request.session:
        return redirect('accounts:login')

    user = request.session['mock_user']
    user_id = user.get('id')
    
    # Cargar pedidos del usuario desde el JSON
    orders_list = []
    if getattr(settings, 'USE_MOCKDB', False):
        repo_root = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(repo_root, 'tests', 'mockdb', 'data')
        orders_path = os.path.join(data_dir, 'orders.json')
        order_items_path = os.path.join(data_dir, 'order_items.json')
        products_path = os.path.join(data_dir, 'products.json')

        try:
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders_data = json.load(f)
            
            with open(order_items_path, 'r', encoding='utf-8') as f:
                order_items_data = json.load(f)
            
            with open(products_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            
            # Filtrar pedidos del usuario
            user_orders = [o for o in orders_data if o.get('customer') == user_id]
            
            # Mapear productos por ID
            products_map = {p.get('id'): p for p in products_data}
            
            # Enriquecer cada pedido con sus items
            for order in user_orders:
                order_id = order.get('id')
                items = [
                    {
                        'product_name': products_map.get(item.get('product'), {}).get('name', 'Producto'),
                        'quantity': item.get('quantity', 1),
                        'price': item.get('price', 0),
                        'size': item.get('size', ''),
                    }
                    for item in order_items_data
                    if item.get('order') == order_id
                ]
                order['items'] = items
                orders_list.append(order)
            
            # Ordenar por ID descendente (más recientes primero)
            orders_list.sort(key=lambda x: x.get('id', 0), reverse=True)
            
        except Exception as e:
            print(f"Error al cargar pedidos: {e}")
    
    return render(request, 'accounts/my_orders.html', {'orders': orders_list})


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
