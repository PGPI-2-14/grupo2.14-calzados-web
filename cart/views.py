from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from shop.models import Product
from .cart import Cart
from .forms import CartAddProductForm

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    # Pasar por Product.objects para forzar el uso del FakeManager en MockDB
    product = get_object_or_404(Product.objects, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        size = cd.get('size') or request.POST.get('size')
        # Use price from form (offer price if available, else regular price)
        price = request.POST.get('price') or product.price
        cart.add(product=product, quantity=cd['quantity'], update_quantity=cd['update'], size=size, price=price)
    return redirect('cart:cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    size = request.POST.get('size')
    cart.remove(product_id, size=size)
    return redirect('cart:cart_detail')

def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return redirect('cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(initial={'quantity': item['quantity'], 'update': True, 'size': item.get('size', '')})
    return render(request, 'cart/detail.html', {'cart': cart})