from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .shipping import compute_shipping
import braintree
from config.braintreeSettings import BRAINTREE_CONF

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
            
            next_id = getattr(Order.objects, '_next_id', 1)
            order = Order.objects.create(
                id=next_id,
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

gateway = braintree.BraintreeGateway(BRAINTREE_CONF)

def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        nonce = request.POST.get('payment_method_nonce')
        
        result = gateway.transaction.sale({
            'amount': str(order.get_total_cost()),
            'payment_method_nonce': nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        
        if result.is_success:
            order.paid = True
            order.braintree_id = result.transaction.id
            order.save()
            return redirect('order:order_created', order.id)
        else:
            return render(request, 'order/payment.html', {
                'order': order,
                'error': result.message,
                'client_token': gateway.client_token.generate()
            })
    else:
        client_token = gateway.client_token.generate()
        return render(request, 'order/payment.html', {
            'order': order,
            'client_token': client_token
        })

def order_created(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order/created.html', {'order': order})