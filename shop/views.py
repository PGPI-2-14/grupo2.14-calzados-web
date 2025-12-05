from django.shortcuts import render, get_object_or_404
from cart.forms import CartAddProductForm
from .models import Category, Product, ProductSize, Brand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    # Get multiple values for each filter using getlist
    selected_brands = request.GET.getlist('brand')
    selected_colors = request.GET.getlist('color')
    selected_materials = request.GET.getlist('material')
    selected_category = request.GET.get('category')
    
    # Category filter - can come from URL slug or query parameter
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    elif selected_category:
        try:
            category = Category.objects.get(slug=selected_category)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            pass
    
    # Brand filter (multiple selection) - Fixed to work with Brand model
    if selected_brands:
        # Filter by brand name or ID
        brand_objects = Brand.objects.filter(name__in=selected_brands)
        if brand_objects:
            products = products.filter(brand__in=brand_objects)
    
    # Color filter (multiple selection)
    if selected_colors:
        products = products.filter(color__in=selected_colors)
    
    # Material filter (multiple selection)
    if selected_materials:
        products = products.filter(material__in=selected_materials)
    
    # Get all unique values for filters from ALL available products
    all_products = Product.objects.filter(available=True)
    brands = list(set([p.brand.name for p in all_products if p.brand]))
    colors = list(set([p.color for p in all_products if p.color]))
    materials = list(set([p.material for p in all_products if p.material]))
    
    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'brands': sorted(brands),
        'colors': sorted(colors),
        'materials': sorted(materials),
        'selected_brands': selected_brands,
        'selected_colors': selected_colors,
        'selected_materials': selected_materials,
    }
    return render(request, 'shop/product/list.html', context)


def product_detail(request, id, slug):
    product = get_object_or_404(Product.objects, id=id, slug=slug, available=True)
    cart_product_form = CartAddProductForm()
    sizes = list(ProductSize.objects.filter(product=product))
    
    # Check if product has stock but no sizes - make it unavailable
    has_sizes = len(sizes) > 0
    # Convert stock to int for comparison
    try:
        product_stock = int(getattr(product, 'stock', 0))
    except (ValueError, TypeError):
        product_stock = 0
    
    has_stock = product_stock > 0
    is_available = product.available and (has_sizes or has_stock)
    
    # If product has stock but no sizes, mark as unavailable
    if has_stock and not has_sizes:
        is_available = False
    
    # Determine stock status message
    if not is_available:
        stock_status = 'agotado'
    elif has_sizes:
        # Check if any size has stock
        total_size_stock = sum(int(getattr(s, 'stock', 0)) for s in sizes)
        stock_status = 'disponible' if total_size_stock > 0 else 'agotado'
    else:
        stock_status = 'disponible' if has_stock else 'agotado'
    
    context = {
        'product': product,
        'cart_product_form': cart_product_form,
        'sizes': sizes,
        'is_available': is_available,
        'has_sizes': has_sizes,
        'stock_status': stock_status,
    }
    return render(request, 'shop/product/detail.html', context)


def home(request):
    all_products = Product.objects.filter(available=True)
    featured_products = list(all_products)[:8]
    return render(request, 'shop/home.html', {'products': featured_products})


def about(request):
    """About Us page"""
    return render(request, 'shop/about.html')


def contact(request):
    """Contact page with form"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if name and email and message:
            try:
                send_mail(
                    f'Nuevo mensaje de contacto de {name}',
                    message,
                    email,
                    [settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, '¡Mensaje enviado correctamente!')
            except Exception as e:
                messages.error(request, f'Error al enviar el mensaje: {str(e)}')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    return render(request, 'shop/contact.html')


def product_search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(available=True)
    
    if query:
        query_lower = query.lower()
        matching_products = []
        
        for product in products:
            # Search in name
            if query_lower in getattr(product, 'name', '').lower():
                matching_products.append(product)
                continue
            
            # Search in description
            if query_lower in getattr(product, 'description', '').lower():
                matching_products.append(product)
                continue
            
            # Search in brand name
            brand = getattr(product, 'brand', None)
            if brand and query_lower in getattr(brand, 'name', '').lower():
                matching_products.append(product)
                continue
            
            # Search in category name
            category = getattr(product, 'category', None)
            if category and query_lower in getattr(category, 'name', '').lower():
                matching_products.append(product)
                continue
        
        products = matching_products
    
    context = {
        'products': products,
        'search_query': query,
        'categories': list(Category.objects.all()),
    }
    return render(request, 'shop/product/list.html', context)
    query = request.GET.get('q', '')
    products = Product.objects.filter(available=True)
    
    if query:
        products = products.filterSearch(name__icontains=query)    
    context = {
        'products': products,
        'search_query': query
    }
    return render(request, 'shop/product/list.html', context)