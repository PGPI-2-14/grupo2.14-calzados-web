from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .shipping import compute_shipping
import braintree
from config.braintreeSettings import BRAINTREE_CONF
import os
from django.core.exceptions import ImproperlyConfigured

def _mockdb_active():
    return os.environ.get('USE_MOCKDB') == '1' or getattr(settings, 'USE_MOCKDB', False)

def _generate_order_number(next_id: int) -> str:
    return f"MOCK-{next_id:04d}"

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            subtotal = float(cart.get_total_price())
            shipping_cost = compute_shipping(subtotal, 'home')
            total = subtotal + shipping_cost
            
            # No forzar id: el FakeManager asigna un id único evitando duplicados
            next_generated_id = getattr(Order.objects, '_next_id', 1)
            order = Order.objects.create(
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                email=cd['email'],
                address=cd['address'],
                postal_code=cd['postal_code'],
                city=cd['city'],
                order_number=_generate_order_number(next_generated_id),
                status='pending',
                subtotal=str(subtotal),
                shipping_cost=str(shipping_cost),
                shipping_method='home',
                taxes='0',
                discount='0',
                total=str(total),
                paid=False,
            )
            for item in cart:
                OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])
            cart.clear()
            # Redirect to payment page
            return redirect('order:payment_process', order.id)
    else:
        form = OrderCreateForm()
    return render(request, 'order/create.html', {'cart': cart, 'form': form})

def _get_braintree_gateway():
    """
    Lazily build and validate a Braintree gateway. Prefer settings.BRAINTREE_CONF,
    then fall back to the imported BRAINTREE_CONF. Raise ImproperlyConfigured if
    credentials are missing.
    """
    conf = getattr(settings, 'BRAINTREE_CONF', None) or globals().get('BRAINTREE_CONF', None)
    if not conf:
        raise ImproperlyConfigured(
            "BRAINTREE_CONF not found. Define settings.BRAINTREE_CONF or set config.braintreeSettings.BRAINTREE_CONF."
        )
    merchant = getattr(conf, 'merchant_id', None)
    public = getattr(conf, 'public_key', None)
    private = getattr(conf, 'private_key', None)
    if not merchant or not public or not private:
        raise ImproperlyConfigured(
            "BRAINTREE_CONF missing credentials (merchant_id/public_key/private_key). "
            "Set BRAINTREE_MERCHANT_ID, BRAINTREE_PUBLIC_KEY and BRAINTREE_PRIVATE_KEY."
        )
    return braintree.BraintreeGateway(conf)


def payment_process(request, order_id):
    # get order (works with mockdb)
    if _mockdb_active():
        try:
            order = Order.objects.get(id=order_id)
        except Exception:
            data = getattr(Order.objects, '_data', [])
            order = next((o for o in data if getattr(o, 'id', None) == order_id), None)
            if not order:
                return render(request, 'order/payment.html', {'error': 'Pedido no encontrado (MockDB).'})
    else:
        order = get_object_or_404(Order, id=order_id)

    # try to create gateway (render friendly error if config is missing)
    try:
        gateway = _get_braintree_gateway()
    except ImproperlyConfigured as e:
        return render(request, 'order/payment.html', {'order': order, 'error': str(e), 'client_token': None})

    if request.method == 'POST':
        nonce = request.POST.get('payment_method_nonce')
        result = gateway.transaction.sale({
            'amount': str(order.get_total_cost()),
            'payment_method_nonce': nonce,
            'options': {'submit_for_settlement': True}
        })

        if result.is_success:
            order.paid = True
            if getattr(result, 'transaction', None) and getattr(result.transaction, 'id', None):
                order.braintree_id = result.transaction.id
            order.save()
            return redirect('order:order_created', order.id)
        else:
            client_token = None
            try:
                client_token = gateway.client_token.generate()
            except Exception:
                pass
            return render(request, 'order/payment.html', {
                'order': order,
                'error': result.message,
                'client_token': client_token
            })
    else:
        client_token = None
        try:
            client_token = gateway.client_token.generate()
        except Exception:
            pass
        return render(request, 'order/payment.html', {'order': order, 'client_token': client_token})

def order_created(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order/created.html', {'order': order})