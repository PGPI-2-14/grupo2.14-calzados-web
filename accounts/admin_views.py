from types import SimpleNamespace
from typing import Any, List

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.utils import require_admin
from accounts.forms import ProductForm
from shop.models import Product, Category, Brand
from order.models import Order, OrderItem


@require_admin
def product_list(request: HttpRequest) -> HttpResponse:
    category_id = request.GET.get('category')
    products = Product.objects.all()
    categories = list(Category.objects.all())
    if category_id:
        try:
            cid = int(category_id)
            cat = Category.objects.get(id=cid)
            products = products.filter(category=cat)
        except Exception:
            pass
    ctx = {
        'products': products,
        'categories': categories,
        'selected_category': int(category_id) if category_id and category_id.isdigit() else None,
    }
    return render(request, 'accounts/admin/products/list.html', ctx)


@require_admin
def product_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            kwargs = form.to_kwargs()
            Product.objects.create(**kwargs)
            return redirect(reverse('accounts:admin_products'))
    else:
        form = ProductForm()
    return render(request, 'accounts/admin/products/form.html', {'form': form, 'mode': 'create'})


@require_admin
def product_edit(request: HttpRequest, id: int) -> HttpResponse:
    # En MockDB, Product.objects.get devuelve un FakeProduct
    product = Product.objects.get(id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            product.name = cd['name']
            product.slug = cd['slug']
            product.description = cd.get('description', '')
            product.price = cd['price']
            product.offer_price = cd.get('offer_price', 0) or 0
            product.available = bool(cd.get('available', False))
            product.stock = cd.get('stock', 0) or 0
            product.is_featured = bool(cd.get('is_featured', False))
            product.gender = cd.get('gender', 'unisex') or 'unisex'
            product.color = cd.get('color', '') or ''
            product.material = cd.get('material', '') or ''
            # Categoría
            cat_id = int(cd['category'])
            product.category = Category.objects.get(id=cat_id)
            # Marca
            brand_id = cd.get('brand')
            product.brand = Brand.objects.get(id=int(brand_id)) if brand_id else None
            # Imagen: asegurar .url
            image_url = cd.get('image_url', '')
            product.image = SimpleNamespace(url=image_url)
            return redirect(reverse('accounts:admin_products'))
    else:
        # Inicializar formulario con datos del producto
        init = {
            'name': getattr(product, 'name', ''),
            'slug': getattr(product, 'slug', ''),
            'description': getattr(product, 'description', ''),
            'price': getattr(product, 'price', 0),
            'offer_price': getattr(product, 'offer_price', 0),
            'available': getattr(product, 'available', True),
            'stock': getattr(product, 'stock', 0),
            'is_featured': getattr(product, 'is_featured', False),
            'gender': getattr(product, 'gender', 'unisex'),
            'color': getattr(product, 'color', ''),
            'material': getattr(product, 'material', ''),
            'category': str(getattr(getattr(product, 'category', None), 'id', '')),
            'brand': str(getattr(getattr(product, 'brand', None), 'id', '')),
            'image_url': getattr(getattr(product, 'image', SimpleNamespace(url='')), 'url', ''),
        }
        form = ProductForm(initial=init)
    return render(request, 'accounts/admin/products/form.html', {'form': form, 'mode': 'edit', 'product_id': id})


@require_admin
def product_delete(request: HttpRequest, id: int) -> HttpResponse:
    # Confirmación sencilla
    if request.method == 'POST':
        # Eliminar del FakeManager: reescribir la lista sin el producto
        remaining = [p for p in Product.objects.all() if getattr(p, 'id', None) != id]
        Product.objects.bulk_set(remaining)
        return redirect(reverse('accounts:admin_products'))
    # Mostrar confirmación
    product = Product.objects.get(id=id)
    return render(request, 'accounts/admin/products/confirm_delete.html', {'product': product})


# -------------------- VENTAS Y PEDIDOS (ADMIN-LITE) --------------------

@require_admin
def sales_dashboard(request: HttpRequest) -> HttpResponse:
    orders = list(Order.objects.all())
    total_orders = len(orders)
    paid_orders = [o for o in orders if getattr(o, 'paid', False)]
    pending_orders = [o for o in orders if str(getattr(o, 'status', '')) in ('pending', 'processing')]

    def order_total(o: Any) -> Any:
        tot = getattr(o, 'total', None)
        if tot not in (None, 0, '0'):
            return tot
        # fallback: sumar items
        items = OrderItem.objects.filter(order=o)
        s = 0
        for it in items:
            s += it.price * it.quantity
        return s

    revenue = sum(order_total(o) for o in orders) if orders else 0
    ctx = {
        'total_orders': total_orders,
        'paid_orders': len(paid_orders),
        'pending_orders': len(pending_orders),
        'revenue': revenue,
        'recent_orders': orders[:10],
    }
    return render(request, 'accounts/admin/dashboard.html', ctx)


@require_admin
def order_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get('status')
    statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    orders_qs = Order.objects.all()
    if status:
        # Simple filter in FakeManager
        orders_qs = orders_qs.filter(status=status)
    ctx = {
        'orders': list(orders_qs),
        'selected_status': status,
        'statuses': statuses,
    }
    return render(request, 'accounts/admin/orders/list.html', ctx)


@require_admin
def order_detail(request: HttpRequest, id: int) -> HttpResponse:
    order = Order.objects.get(id=id)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'accounts/admin/orders/detail.html', {
        'order': order,
        'items': list(items),
        'statuses': ['pending', 'processing', 'shipped', 'delivered', 'cancelled'],
    })


@require_admin
def order_update_status(request: HttpRequest, id: int) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('accounts:admin_order_detail', args=[id]))
    order = Order.objects.get(id=id)
    new_status = request.POST.get('status') or getattr(order, 'status', 'pending')
    paid_flag = request.POST.get('paid')
    order.status = new_status
    if paid_flag is not None:
        order.paid = bool(paid_flag)
    return redirect(reverse('accounts:admin_order_detail', args=[id]))
