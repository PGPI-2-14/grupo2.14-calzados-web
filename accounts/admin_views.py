# Complete fixed version of accounts/admin_views.py

from types import SimpleNamespace
from typing import Any, List

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal

from accounts.utils import require_admin
from accounts.forms import ProductForm, DeliveryForm, PaymentForm, CustomerForm
from accounts.models import UserAccount
from shop.models import Product, Category, Brand
from order.models import Order, OrderItem
from cart.cart import Cart
from order.shipping import compute_shipping, method_name

# Persistencia MockDB
try:
    from tests.mockdb.patcher import (
        save_products_to_fixture,
        save_orders_to_fixture,
        save_order_items_to_fixture,
        save_user_accounts_to_fixture,
        save_categories_to_fixture,
        save_brands_to_fixture,
    )
except Exception:
    def save_products_to_fixture():
        pass
    def save_orders_to_fixture():
        pass
    def save_order_items_to_fixture():
        pass
    def save_user_accounts_to_fixture():
        pass
    def save_categories_to_fixture():
        pass
    def save_brands_to_fixture():
        pass


@require_admin
def product_list(request: HttpRequest) -> HttpResponse:
    """Product list with working filters"""
    # Get filter parameters
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    search_query = request.GET.get('q')
    
    # Start with all products
    products = list(Product.objects.all())
    categories = list(Category.objects.all())
    
    # Apply category filter
    if category_id and category_id.isdigit():
        try:
            cid = int(category_id)
            products = [p for p in products if getattr(getattr(p, 'category', None), 'id', None) == cid]
        except Exception:
            pass
    
    # Apply status filter  
    if status == 'available':
        products = [p for p in products if getattr(p, 'available', False)]
    elif status == 'out_of_stock':
        products = [p for p in products if getattr(p, 'stock', 0) == 0]
    
    # Apply search filter
    if search_query:
        search_lower = search_query.lower()
        products = [p for p in products if search_lower in getattr(p, 'name', '').lower() or 
                   search_lower in getattr(p, 'description', '').lower()]
    
    ctx = {
        'products': products,
        'categories': categories,
        'selected_category': int(category_id) if category_id and category_id.isdigit() else None,
        'selected_status': status,
        'search_query': search_query,
    }
    return render(request, 'accounts/admin/products/list.html', ctx)


@require_admin
def product_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        from shop.models import ProductSize
        
        # Handle new category
        category_value = request.POST.get('category', '')
        if category_value.startswith('new:'):
            cat_name = category_value.replace('new:', '')
            cat_slug = cat_name.lower().replace(' ', '-')
            next_cat_id = max([getattr(c, 'id', 0) for c in Category.objects.all()], default=0) + 1
            new_cat = Category.objects.create(id=next_cat_id, name=cat_name, slug=cat_slug)
            category_id = new_cat.id
            save_categories_to_fixture()
        else:
            category_id = int(category_value)
        
        # Handle new brand
        brand_value = request.POST.get('brand', '')
        brand_id = None
        if brand_value:
            if brand_value.startswith('new:'):
                brand_name = brand_value.replace('new:', '')
                next_brand_id = max([getattr(b, 'id', 0) for b in Brand.objects.all()], default=0) + 1
                new_brand = Brand.objects.create(id=next_brand_id, name=brand_name, image=SimpleNamespace(url=''))
                brand_id = new_brand.id
                save_brands_to_fixture()
            else:
                brand_id = int(brand_value)
        
        # Create product
        category = Category.objects.get(id=category_id)
        brand = Brand.objects.get(id=brand_id) if brand_id else None
        
        # Get next product ID
        next_product_id = max([getattr(p, 'id', 0) for p in Product.objects.all()], default=0) + 1
        
        # Handle offer_price: if empty or 0, don't set an offer
        offer_price_val = request.POST.get('offer_price', '').strip()
        if offer_price_val and float(offer_price_val) > 0:
            offer_price = offer_price_val
        else:
            offer_price = 0
        
        product = Product.objects.create(
            id=next_product_id,
            name=request.POST.get('name'),
            slug=request.POST.get('slug'),
            description=request.POST.get('description', ''),
            price=request.POST.get('price'),
            offer_price=offer_price,
            stock=request.POST.get('stock', 0) or 0,
            available=bool(request.POST.get('available')),
            is_featured=bool(request.POST.get('is_featured')),
            gender=request.POST.get('gender', 'unisex'),
            color=request.POST.get('color', ''),
            material=request.POST.get('material', ''),
            category=category,
            brand=brand,
            image=SimpleNamespace(url=request.POST.get('image_url', ''))
        )
        
        # Handle sizes
        sizes = request.POST.getlist('sizes[]')
        stocks = request.POST.getlist('size_stocks[]')
        for size, stock in zip(sizes, stocks):
            if size and stock:
                next_size_id = max([getattr(s, 'id', 0) for s in ProductSize.objects.all()], default=0) + 1
                ProductSize.objects.create(
                    id=next_size_id,
                    product=product,
                    size=size.strip(),
                    stock=int(stock)
                )
        
        save_products_to_fixture()
        messages.success(request, f'Producto "{product.name}" creado exitosamente.')
        
        # Reload MockDB to ensure all stats stay consistent
        try:
            from tests.mockdb.patcher import MockDB
            MockDB().apply()
        except Exception:
            pass
        
        return redirect(reverse('accounts:admin_products'))
    
    categories = list(Category.objects.all())
    brands = list(Brand.objects.all())
    return render(request, 'accounts/admin/products/form.html', {
        'categories': categories,
        'brands': brands,
        'mode': 'create'
    })


@require_admin
def product_edit(request: HttpRequest, id: int) -> HttpResponse:
    """Edit product with proper brand loading"""
    from shop.models import ProductSize
    product = Product.objects.get(id=id)
    sizes = list(ProductSize.objects.filter(product=product))
    
    if request.method == 'POST':
        # Handle category (new or existing)
        category_value = request.POST.get('category', '')
        if category_value.startswith('new:'):
            cat_name = category_value.replace('new:', '')
            cat_slug = cat_name.lower().replace(' ', '-')
            next_cat_id = max([getattr(c, 'id', 0) for c in Category.objects.all()], default=0) + 1
            new_cat = Category.objects.create(id=next_cat_id, name=cat_name, slug=cat_slug)
            product.category = new_cat
            save_categories_to_fixture()
        else:
            cat_id = int(category_value)
            product.category = Category.objects.get(id=cat_id)
        
        # Handle brand (new or existing)
        brand_value = request.POST.get('brand', '')
        if brand_value:
            if brand_value.startswith('new:'):
                brand_name = brand_value.replace('new:', '')
                next_brand_id = max([getattr(b, 'id', 0) for b in Brand.objects.all()], default=0) + 1
                new_brand = Brand.objects.create(id=next_brand_id, name=brand_name, image=SimpleNamespace(url=''))
                product.brand = new_brand
                save_brands_to_fixture()
            else:
                product.brand = Brand.objects.get(id=int(brand_value))
        else:
            product.brand = None
        
        # Update product fields
        product.name = request.POST.get('name')
        product.slug = request.POST.get('slug')
        product.description = request.POST.get('description', '')
        product.price = request.POST.get('price')
        offer_price_val = request.POST.get('offer_price', '').strip()
        if offer_price_val and float(offer_price_val) > 0:
            product.offer_price = offer_price_val
        else:
            product.offer_price = 0
        product.stock = request.POST.get('stock', 0) or 0
        product.available = bool(request.POST.get('available'))
        product.is_featured = bool(request.POST.get('is_featured'))
        product.gender = request.POST.get('gender', 'unisex')
        product.color = request.POST.get('color', '')
        product.material = request.POST.get('material', '')
        image_url = request.POST.get('image_url', '')
        product.image = SimpleNamespace(url=image_url)
        
        # Update sizes - remove old ones and add new ones
        remaining_sizes = [s for s in ProductSize.objects._items if getattr(getattr(s, 'product', None), 'id', None) != product.id]
        
        new_sizes = request.POST.getlist('sizes[]')
        new_stocks = request.POST.getlist('size_stocks[]')
        
        for size_name, stock in zip(new_sizes, new_stocks):
            if size_name and stock:
                next_size_id = max([getattr(s, 'id', 0) for s in ProductSize.objects.all()], default=0) + 1
                new_size = ProductSize.objects.create(
                    id=next_size_id,
                    product=product,
                    size=size_name.strip(),
                    stock=int(stock)
                )
                remaining_sizes.append(new_size)
        
        ProductSize.objects.bulk_set(remaining_sizes)
        
        save_products_to_fixture()
        messages.success(request, f'Producto "{product.name}" actualizado exitosamente.')
        
        # Reload MockDB to ensure all stats stay consistent
        try:
            from tests.mockdb.patcher import MockDB
            MockDB().apply()
        except Exception:
            pass
        
        return redirect(reverse('accounts:admin_products'))
    
    categories = list(Category.objects.all())
    brands = list(Brand.objects.all())
    
    current_category_id = getattr(getattr(product, 'category', None), 'id', None)
    
    product_brand = getattr(product, 'brand', None)
    current_brand_id = None
    if product_brand is not None:
        current_brand_id = getattr(product_brand, 'id', None)
    
    return render(request, 'accounts/admin/products/form.html', {
        'product': product,
        'sizes': sizes,
        'categories': categories,
        'brands': brands,
        'current_category_id': current_category_id,
        'current_brand_id': current_brand_id,
        'mode': 'edit'
    })


@require_admin
def product_delete(request: HttpRequest, id: int) -> HttpResponse:
    """Delete product and cleanup orphaned brands/categories"""
    try:
        product = Product.objects.get(id=id)
    except Exception:
        messages.error(request, 'Producto no encontrado.')
        return redirect(reverse('accounts:admin_products'))
    
    if request.method == 'POST':
        product_name = getattr(product, 'name', '')
        
        # Store category and brand before deletion
        product_category = getattr(product, 'category', None)
        product_brand = getattr(product, 'brand', None)
        
        product_category_id = getattr(product_category, 'id', None) if product_category else None
        product_brand_id = getattr(product_brand, 'id', None) if product_brand else None
        
        # Delete product from list
        remaining_products = [p for p in Product.objects.all() if getattr(p, 'id', None) != id]
        Product.objects.bulk_set(remaining_products)
        
        # Check if category should be deleted
        if product_category_id:
            category_in_use = False
            for p in remaining_products:
                p_cat = getattr(p, 'category', None)
                if p_cat and getattr(p_cat, 'id', None) == product_category_id:
                    category_in_use = True
                    break
            
            if not category_in_use:
                remaining_categories = [c for c in Category.objects.all() 
                                       if getattr(c, 'id', None) != product_category_id]
                Category.objects.bulk_set(remaining_categories)
                save_categories_to_fixture()
                print(f"[admin] Deleted orphaned category: {getattr(product_category, 'name', 'Unknown')}")
        
        # Check if brand should be deleted
        if product_brand_id:
            brand_in_use = False
            for p in remaining_products:
                p_brand = getattr(p, 'brand', None)
                if p_brand and getattr(p_brand, 'id', None) == product_brand_id:
                    brand_in_use = True
                    break
            
            if not brand_in_use:
                remaining_brands = [b for b in Brand.objects.all() 
                                   if getattr(b, 'id', None) != product_brand_id]
                Brand.objects.bulk_set(remaining_brands)
                save_brands_to_fixture()
                print(f"[admin] Deleted orphaned brand: {getattr(product_brand, 'name', 'Unknown')}")
        
        save_products_to_fixture()
        messages.success(request, f'Producto "{product_name}" eliminado exitosamente.')
        
        try:
            from tests.mockdb.patcher import MockDB
            MockDB().apply()
        except Exception:
            pass
        
        return redirect(reverse('accounts:admin_products'))
    
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
            # Get next customer ID
            next_id = max([getattr(c, 'id', 0) for c in UserAccount.objects.all()], default=0) + 1
            
            kwargs = form.to_kwargs()
            kwargs['id'] = next_id
            UserAccount.objects.create(**kwargs)
            save_user_accounts_to_fixture()
            
            # Reload MockDB to ensure all stats stay consistent
            try:
                from tests.mockdb.patcher import MockDB
                MockDB().apply()
            except Exception:
                pass
            
            messages.success(request, 'Cliente creado exitosamente.')
            return redirect(reverse('accounts:admin_customers'))
    else:
        form = CustomerForm()
    return render(request, 'accounts/admin/customers/form.html', {'form': form, 'mode': 'create'})


@require_admin
def customer_edit(request: HttpRequest, id: int) -> HttpResponse:
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
            try:
                customer.save()
            except Exception:
                pass
            save_user_accounts_to_fixture()
            messages.success(request, 'Cliente actualizado exitosamente.')
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
    return render(request, 'accounts/admin/customers/form.html', {'form': form, 'mode': 'edit', 'customer': customer})


@require_admin
def customer_delete(request: HttpRequest, id: int) -> HttpResponse:
    if request.method == 'POST':
        try:
            u = UserAccount.objects.get(id=id, role=UserAccount.ROLE_CUSTOMER)
            customer_name = f"{u.first_name} {u.last_name}"
            remaining = [c for c in UserAccount.objects.all() if getattr(c, 'id', None) != id]
            UserAccount.objects.bulk_set(remaining)
        except Exception:
            customer_name = "Cliente"
        save_user_accounts_to_fixture()
        messages.success(request, f'Cliente "{customer_name}" eliminado exitosamente.')
        return redirect(reverse('accounts:admin_customers'))
    customer = UserAccount.objects.get(id=id, role=UserAccount.ROLE_CUSTOMER)
    return render(request, 'accounts/admin/customers/confirm_delete.html', {'customer': customer})


# -------------------- VENTAS Y PEDIDOS (ADMIN-LITE) --------------------

@require_admin
def sales_dashboard(request: HttpRequest) -> HttpResponse:
    """Dashboard simplificado con estadísticas clave"""
    
    # Get all orders
    orders = list(Order.objects.all())
    total_orders = len(orders)
    
    # Calculate paid and pending orders
    paid_orders = [o for o in orders if getattr(o, 'paid', False)]
    pending_orders = [o for o in orders if str(getattr(o, 'status', '')) in ('pending', 'processing')]

    def order_total(o: Any) -> Decimal:
        tot = getattr(o, 'total', None)
        if tot not in (None, 0, '0'):
            try:
                return Decimal(str(tot))
            except:
                return Decimal('0')
        # Fallback: calculate from items
        items = [item for item in OrderItem.objects._items if getattr(item, 'order', None) == o or getattr(getattr(item, 'order', None), 'id', None) == o.id]
        s = Decimal('0')
        for it in items:
            try:
                s += Decimal(str(getattr(it, 'price', 0))) * getattr(it, 'quantity', 1)
            except:
                pass
        return s

    revenue = sum(order_total(o) for o in orders) if orders else Decimal('0')
    average_order_value = revenue / Decimal(str(total_orders)) if total_orders > 0 else Decimal('0')
    
    # Calculate additional stats
    products = list(Product.objects.all())
    total_products = len(products)
    low_stock_products = len([p for p in products if getattr(p, 'stock', 0) < 10 and getattr(p, 'stock', 0) > 0])
    
    customers = list(UserAccount.objects.filter(role=UserAccount.ROLE_CUSTOMER))
    total_customers = len(customers)
    
    # Get recent orders (max 10)
    recent_orders = sorted(orders, key=lambda x: getattr(x, 'created', ''), reverse=True)[:10]
    
    ctx = {
        'total_orders': total_orders,
        'paid_orders': len(paid_orders),
        'pending_orders': len(pending_orders),
        'revenue': revenue,
        'total_revenue': revenue,
        'average_order_value': average_order_value,
        'recent_orders': recent_orders,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'total_customers': total_customers,
    }
    return render(request, 'accounts/admin/dashboard.html', ctx)


@require_admin
def order_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get('status')
    statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    orders = list(Order.objects.all())
    
    if status:
        orders = [o for o in orders if getattr(o, 'status', '') == status]
    
    ctx = {
        'orders': orders,
        'selected_status': status,
        'statuses': statuses,
    }
    return render(request, 'accounts/admin/orders/list.html', ctx)


@require_admin
def order_detail(request: HttpRequest, id: int) -> HttpResponse:
    order = Order.objects.get(id=id)
    # Get items for this order
    items = [item for item in OrderItem.objects._items if getattr(getattr(item, 'order', None), 'id', None) == id]
    return render(request, 'accounts/admin/orders/detail.html', {
        'order': order,
        'items': items,
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
    save_orders_to_fixture()
    messages.success(request, f'Estado del pedido actualizado a "{new_status}".')
    return redirect(reverse('accounts:admin_order_detail', args=[id]))


@require_admin
def order_delete(request: HttpRequest, id: int) -> HttpResponse:
    """Delete an order and its items"""
    if request.method == 'POST':
        # Get order number before deletion
        try:
            order = Order.objects.get(id=id)
            order_number = getattr(order, 'order_number', f'#{id}')
        except:
            order_number = f'#{id}'
        
        # Delete order items first
        remaining_items = [item for item in OrderItem.objects._items if getattr(getattr(item, 'order', None), 'id', None) != id]
        OrderItem.objects.bulk_set(remaining_items)
        
        # Delete order
        remaining_orders = [o for o in Order.objects.all() if getattr(o, 'id', None) != id]
        Order.objects.bulk_set(remaining_orders)
        
        save_orders_to_fixture()
        save_order_items_to_fixture()
        messages.success(request, f'Pedido "{order_number}" eliminado exitosamente.')
        return redirect(reverse('accounts:admin_orders'))
    
    order = Order.objects.get(id=id)
    return render(request, 'accounts/admin/orders/confirm_delete.html', {'order': order})


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
            order_status = 'processing' if payment_method == 'cod' else 'pending'
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
                try:
                    prod = item['product']
                    qty = int(item['quantity'])
                    if hasattr(prod, 'stock'):
                        prod.stock = max(0, int(getattr(prod, 'stock', 0)) - qty)
                except Exception:
                    pass
            save_orders_to_fixture()
            save_order_items_to_fixture()
            save_products_to_fixture()
            cart.clear()
            request.session.pop(ADMIN_CHECKOUT_KEY, None)
            return render(request, 'accounts/admin/checkout/created.html', {'order': order})
    else:
        form = PaymentForm()
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