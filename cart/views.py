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

@require_POST
def cart_update_quantity(request, product_id):
    """Update quantity of a specific product (with size) in cart"""
    cart = Cart(request)
    size = request.POST.get('size')
    quantity = int(request.POST.get('quantity', 1))
    
    # Ensure quantity is at least 1
    if quantity < 1:
        quantity = 1
    
    product = get_object_or_404(Product.objects, id=product_id)
    cart.add(product=product, quantity=quantity, update_quantity=True, size=size)
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
    # No need to add forms anymore since we use +/- buttons
    return render(request, 'cart/detail.html', {'cart': cart})