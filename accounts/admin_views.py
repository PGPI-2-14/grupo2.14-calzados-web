from types import SimpleNamespace
from typing import Any, List

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.utils import require_admin
from accounts.forms import ProductForm, DeliveryForm, PaymentForm, CustomerForm
from accounts.models import UserAccount
from shop.models import Product, Category, Brand
from order.models import Order, OrderItem
from cart.cart import Cart
from order.shipping import compute_shipping, method_name


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


@require_admin
def customer_list(request: HttpRequest) -> HttpResponse:
    """Listado simple de clientes (users con role 'customer')."""
    customers = UserAccount.objects.filter(role=UserAccount.ROLE_CUSTOMER)
    return render(request, 'accounts/admin/customers/list.html', {'customers': list(customers)})


@require_admin
def customer_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            kwargs = form.to_kwargs()
            # password_hash no lo solicitamos en admin-lite; dejar vacío
            UserAccount.objects.create(**kwargs)
            return redirect(reverse('accounts:admin_customers'))
    else:
        form = CustomerForm()
    return render(request, 'accounts/admin/customers/form.html', {'form': form, 'mode': 'create'})


@require_admin
def customer_edit(request: HttpRequest, id: int) -> HttpResponse:
    # Asegurar que solo editamos cuentas de rol 'customer'
    customer = UserAccount.objects.get(id=id, role=UserAccount.ROLE_CUSTOMER)
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            customer.email = cd.get('email', customer.email)
            customer.role = cd.get('role', customer.role)
            customer.first_name = cd.get('first_name', customer.first_name)
            customer.last_name = cd.get('last_name', customer.last_name)
            customer.is_active = bool(cd.get('is_active', True))
            # Si es un modelo real, guardar cambios
            try:
                customer.save()
            except Exception:
                # En el escenario MockDB, puede que no exista save()
                pass
            return redirect(reverse('accounts:admin_customers'))
    else:
        init = {
            'email': getattr(customer, 'email', ''),
            'role': getattr(customer, 'role', UserAccount.ROLE_CUSTOMER),
            'first_name': getattr(customer, 'first_name', ''),
            'last_name': getattr(customer, 'last_name', ''),
            'is_active': getattr(customer, 'is_active', True),
        }
        form = CustomerForm(initial=init)
    return render(request, 'accounts/admin/customers/form.html', {'form': form, 'mode': 'edit', 'customer_id': id})


@require_admin
def customer_delete(request: HttpRequest, id: int) -> HttpResponse:
    if request.method == 'POST':
        # Intentar borrar el registro
        try:
            u = UserAccount.objects.get(id=id, role=UserAccount.ROLE_CUSTOMER)
            u.delete()
        except Exception:
            # En caso de MockDB, sobrescribir si hace falta
            remaining = [c for c in UserAccount.objects.filter(role=UserAccount.ROLE_CUSTOMER) if getattr(c, 'id', None) != id]
            try:
                UserAccount.objects.bulk_set(remaining)
            except Exception:
                pass
        return redirect(reverse('accounts:admin_customers'))
    customer = UserAccount.objects.get(id=id, role=UserAccount.ROLE_CUSTOMER)
    return render(request, 'accounts/admin/customers/confirm_delete.html', {'customer': customer})


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


# -------------------- CHECKOUT (ADMIN-LITE, SOLO PRUEBAS) --------------------

ADMIN_CHECKOUT_KEY = 'admin_checkout_data'


@require_admin
def checkout_delivery(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    if request.method == 'POST':
        form = DeliveryForm(request.POST)
        if form.is_valid():
            request.session[ADMIN_CHECKOUT_KEY] = form.cleaned_data
            return redirect(reverse('accounts:admin_checkout_payment'))
    else:
        form = DeliveryForm()
    # Estimación con método por defecto
    subtotal = float(cart.get_total_price())
    method_code = form.fields['shipping_method'].initial or 'home'
    shipping_estimate = compute_shipping(subtotal, method_code)
    total_estimate = subtotal + shipping_estimate
    return render(request, 'accounts/admin/checkout/delivery.html', {
        'cart': cart,
        'form': form,
        'shipping_estimate': shipping_estimate,
        'total_estimate': total_estimate,
        'selected_method': method_code,
    })


@require_admin
def checkout_payment(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    data = request.session.get(ADMIN_CHECKOUT_KEY) or {}
    if not data:
        return redirect(reverse('accounts:admin_checkout_delivery'))
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            subtotal = float(cart.get_total_price())
            method_code = data.get('shipping_method', 'home')
            shipping_cost = compute_shipping(subtotal, method_code)
            total = subtotal + shipping_cost
            # Si el cliente elige contrareembolso, aceptamos el pedido (estado 'processing') sin marcar como pagado.
            order_status = 'processing' if payment_method == 'cod' else 'pending'
            # Crear pedido en MockDB
            next_id = getattr(Order.objects, '_next_id', 1)
            order = Order.objects.create(
                id=next_id,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                email=data.get('email', ''),
                address=data.get('address', ''),
                postal_code=data.get('postal_code', ''),
                city=data.get('city', ''),
                order_number=f"MOCK-{next_id:04d}",
                status=order_status,
                subtotal=str(subtotal),
                shipping_cost=str(shipping_cost),
                shipping_method=method_code,
                taxes='0', discount='0', total=str(total),
                paid=bool(payment_method == 'gateway'),
                payment_method=payment_method,
            )
            for item in cart:
                OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])
            cart.clear()
            request.session.pop(ADMIN_CHECKOUT_KEY, None)
            return render(request, 'accounts/admin/checkout/created.html', {'order': order})
    else:
        form = PaymentForm()
    # Resumen
    subtotal = float(cart.get_total_price())
    method_code = data.get('shipping_method', 'home')
    shipping_cost = compute_shipping(subtotal, method_code)
    total = subtotal + shipping_cost
    return render(request, 'accounts/admin/checkout/payment.html', {
        'cart': cart,
        'form': form,
        'delivery': data,
        'shipping_method_name': method_name(method_code),
        'shipping_cost': shipping_cost,
        'subtotal': subtotal,
        'total': total,
    })
