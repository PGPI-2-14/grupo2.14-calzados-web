from django.shortcuts import render, get_object_or_404, redirect
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .shipping import compute_shipping

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
            # Crear pedido vía MockDB
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
            return render(request, 'order/payment.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'order/create.html', {'cart': cart, 'form': form})

def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    '''
    if request.method == 'POST':
        order.paid = True
        order.save()
    '''
    
    return redirect('order:order_created', order.id)
#return render(request, 'order/payment.html', {'order': order})

def order_created(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order/created.html', {'order': order})
