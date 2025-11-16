from django.shortcuts import render, get_object_or_404
from cart.forms import CartAddProductForm
from .models import Category, Product, ProductSize

# from django.views import generic

# class IndexView(generic.ListView):
#     template_name = 'shop/index.html'
#     context_object_name = 'products'

#     def get_queryset(self):
#         '''Return five lattest products
#         '''
#         return Product.objects.filter(created__lte=timezone.now()
#         ).order_by('-created')[:5]



def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    selected_brand = request.GET.get('brand')
    selected_color = request.GET.get('color')
    selected_material = request.GET.get('material')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    if selected_brand:
        products = [p for p in products if p.brand and p.brand.name == selected_brand]
    
    if selected_color:
        products = [p for p in products if p.color == selected_color]
    
    if selected_material:
        products = [p for p in products if p.material == selected_material]
    
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
        'selected_brand': selected_brand,
        'selected_color': selected_color,
        'selected_material': selected_material,
    }
    return render(request, 'shop/product/list.html', context)


# class ProductListView(generic.ListView):
#     template_name = 'shop/product/list.html'

#     def get_queryset(self):
#         return Product.objects.filter(available=True)

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         category = None
#         if category_slug:
#             category = get_object_or_404(Category, slug=category_slug)
#         context['category'] = category
#         context['categories'] = Category.objects.all()





def product_detail(request, id, slug):
    # Usar Product.objects para que en modo MockDB pase por el FakeManager/FakeQuerySet
    product = get_object_or_404(Product.objects, id=id, slug=slug, available=True)
    cart_product_form = CartAddProductForm()
    sizes = list(ProductSize.objects.filter(product=product))
    context = {'product': product, 'cart_product_form': cart_product_form, 'sizes': sizes}
    return render(request, 'shop/product/detail.html', context)


# class ProductDetialView(generic.DetailView):

#     template_name = 'shop/product/detail.html'
#     model = Product
#     form_class = CartAddProductForm

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['products'] = get_object_or_404(Product, 
#         id=id, slug=slug, available=True)
#         return context

def home(request):
    all_products = Product.objects.filter(available=True)
    featured_products = list(all_products)[:8]
    return render(request, 'shop/home.html', {'products': featured_products})