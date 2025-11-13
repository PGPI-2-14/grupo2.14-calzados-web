from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .shipping import compute_shipping
from .utils import send_order_confirmation
try:
    # Persistencia MockDB
    from tests.mockdb.patcher import save_orders_to_fixture, save_order_items_to_fixture, save_products_to_fixture
except Exception:
    # En entorno sin MockDB disponible, no persistimos
    def save_orders_to_fixture():
        pass
    def save_order_items_to_fixture():
        pass
    def save_products_to_fixture():
        pass

def _generate_order_number(next_id: int) -> str:
    return f"MOCK-{next_id:04d}"

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Subtotal del carrito y envío por defecto (domicilio)
            subtotal = float(cart.get_total_price())
            shipping_cost = compute_shipping(subtotal, 'home')
            total = subtotal + shipping_cost
            # Si el usuario está logueado como customer, asociar el pedido al Customer
            customer_obj = None
            try:
                from accounts.utils import SESSION_USER_ROLE, SESSION_USER_ID
                role = request.session.get(SESSION_USER_ROLE)
                user_id = request.session.get(SESSION_USER_ID)
                if str(role) == 'customer' and user_id:
                    try:
                        from .models import Customer as OrderCustomer
                        customer_obj = OrderCustomer.objects.get(id=int(user_id))
                    except Exception:
                        # Fallback: intentar por email del formulario
                        try:
                            customer_obj = OrderCustomer.objects.filter(email=cd.get('email', '')).first()
                        except Exception:
                            customer_obj = None
            except Exception:
                customer_obj = None
            # Crear pedido vía MockDB
            next_id = getattr(Order.objects, '_next_id', 1)
            order = Order.objects.create(
                id=next_id,
                customer=customer_obj,
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                email=cd['email'],
                address=cd['address'],
                postal_code=cd['postal_code'],
                city=cd['city'],
                order_number=_generate_order_number(next_id),
                status='pending',
                subtotal=str(subtotal),
                shipping_cost=str(shipping_cost),
                shipping_method='home',
                # Guardar dirección de envío explícita cuando es envío a domicilio
                shipping_address=cd['address'],
                taxes='0',
                discount='0',
                total=str(total),
                paid=False,
            )
            for item in cart:
                OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])
                # Decrementar stock del producto
                try:
                    prod = item['product']
                    qty = int(item['quantity'])
                    if hasattr(prod, 'stock'):
                        prod.stock = max(0, int(getattr(prod, 'stock', 0)) - qty)
                except Exception:
                    pass
            # Persistir inmediatamente el pedido y sus líneas en JSON (MockDB)
            try:
                save_orders_to_fixture()
                save_order_items_to_fixture()
                save_products_to_fixture()
            except Exception:
                pass
            # Enviar email de confirmación (no bloqueante si falla)
            try:
                send_order_confirmation(order)
            except Exception:
                pass
            cart.clear()
            return render(request, 'order/payment.html', {'order': order})
    else:
        form = OrderCreateForm()
    # También calcular resumen con envío para la vista GET
    subtotal = float(cart.get_total_price())
    shipping_cost = compute_shipping(subtotal, 'home')
    total = subtotal + shipping_cost
    return render(request, 'order/create.html', {
        'cart': cart,
        'form': form,
        'shipping_cost': shipping_cost,
        'subtotal': subtotal,
        'total': total,
    })

def payment_process(request, order_id):
    # Forzar manager mock: evita tocar ORM real si MockDB no parcheó _default_manager
    order = get_object_or_404(Order.objects, id=order_id)
    # Simular confirmación de pago: marcar según método y persistir
    if request.method == 'POST':
        method = request.POST.get('payment_method', '').strip() or 'card'
        try:
            order.payment_method = method
        except Exception:
            pass
        if method == 'card':
            order.paid = True
            try:
                order.status = 'paid'
            except Exception:
                pass
        elif method in ('contrareembolso', 'cod', 'cash_on_delivery'):
            order.paid = False
            try:
                # Aceptado pero pendiente de cobro
                order.status = 'processing'
            except Exception:
                pass
        try:
            save_orders_to_fixture()
        except Exception:
            pass
    # Redirigir con flag para descargar simulación del email
    return redirect(f"{reverse('order:order_created', args=[order.id])}?download=1")
#return render(request, 'order/payment.html', {'order': order})

def order_created(request, order_id):
    # Forzar manager mock: evita tocar ORM real si MockDB no parcheó _default_manager
    order = get_object_or_404(Order.objects, id=order_id)
    # Si venimos de la pasarela con GET (flujo temporal), actualizar paid según método
    method = (request.GET.get('payment_method') or '').strip()
    if method:
        try:
            order.payment_method = method
        except Exception:
            pass
        paid_before = getattr(order, 'paid', False)
        if method == 'card' and not paid_before:
            order.paid = True
            try:
                order.status = 'paid'
            except Exception:
                pass
        elif method in ('contrareembolso', 'cod', 'cash_on_delivery'):
            order.paid = False
            try:
                order.status = 'processing'
            except Exception:
                pass
        try:
            save_orders_to_fixture()
        except Exception:
            pass
    download_flag = (request.GET.get('download') == '1')
    return render(request, 'order/created.html', {'order': order, 'download': '1' if download_flag else ''})

def order_email_download(request, order_id):
    # Genera un archivo descargable con el contenido del email de confirmación
    order = get_object_or_404(Order.objects, id=order_id)
    items = list(OrderItem.objects.filter(order=order))
    ctx = {'order': order, 'items': items}
    subject = f"Confirmación de pedido {getattr(order, 'order_number', order.id)}"
    body = render_to_string('order/emails/confirmation.txt', ctx)
    # Añadir cabeceras sencillas
    content = f"To: {getattr(order, 'email', '')}\nSubject: {subject}\n\n{body}"
    filename = f"pedido-{getattr(order, 'order_number', order.id)}.txt"
    resp = HttpResponse(content, content_type='text/plain; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
