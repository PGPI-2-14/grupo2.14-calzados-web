from typing import List, Tuple
from django import forms
from shop.models import Category, Product, Brand
from order.shipping import method_choices


class ProductForm(forms.Form):
    name = forms.CharField(max_length=200, label='Nombre')
    slug = forms.SlugField(max_length=200, label='Slug')
    description = forms.CharField(widget=forms.Textarea, required=False, label='Descripción')
    price = forms.DecimalField(max_digits=10, decimal_places=2, label='Precio')
    offer_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False, initial=0, label='Precio oferta')
    available = forms.BooleanField(required=False, initial=True, label='Disponible')
    stock = forms.IntegerField(min_value=0, initial=0, label='Stock')
    is_featured = forms.BooleanField(required=False, initial=False, label='Destacado')
    gender = forms.CharField(max_length=30, required=False, initial='unisex', label='Género')
    color = forms.CharField(max_length=50, required=False, label='Color')
    material = forms.CharField(max_length=80, required=False, label='Material')
    category = forms.ChoiceField(label='Categoría')
    brand = forms.ChoiceField(label='Marca', required=False)
    image_url = forms.CharField(max_length=500, required=False, label='URL de imagen')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Cargar categorías desde MockDB
        cat_choices: List[Tuple[str, str]] = [(str(c.id), c.name) for c in Category.objects.all()]
        self.fields['category'].choices = cat_choices
        brand_choices: List[Tuple[str, str]] = [('', '— Sin marca —')] + [(str(b.id), b.name) for b in Brand.objects.all()]
        self.fields['brand'].choices = brand_choices

    def to_kwargs(self) -> dict:
        """Convierte los datos del formulario a kwargs compatibles con Product.objects.create() en MockDB."""
        cd = self.cleaned_data
        # Encontrar la categoría seleccionada
        cat_id = int(cd['category'])
        category = Category.objects.get(id=cat_id)
        kwargs = dict(
            name=cd['name'],
            slug=cd['slug'],
            description=cd.get('description', ''),
            price=cd['price'],
            available=bool(cd.get('available', False)),
            category=category,
            image=cd.get('image_url', ''),
            offer_price=cd.get('offer_price', 0) or 0,
            gender=cd.get('gender', 'unisex') or 'unisex',
            color=cd.get('color', '') or '',
            material=cd.get('material', '') or '',
            stock=cd.get('stock', 0) or 0,
            is_featured=bool(cd.get('is_featured', False)),
        )
        brand_id = cd.get('brand')
        if brand_id:
            brand = Brand.objects.get(id=int(brand_id))
            kwargs['brand'] = brand
        return kwargs


class DeliveryForm(forms.Form):
    first_name = forms.CharField(label='Nombre', max_length=50)
    last_name = forms.CharField(label='Apellidos', max_length=50)
    email = forms.EmailField(label='Email')
    address = forms.CharField(label='Dirección', max_length=250)
    postal_code = forms.CharField(label='Código postal', max_length=20)
    city = forms.CharField(label='Ciudad', max_length=100)
    shipping_method = forms.ChoiceField(label='Forma de entrega', choices=(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shipping_method'].choices = method_choices()
        self.fields['shipping_method'].initial = 'home'


class PaymentForm(forms.Form):
    PAYMENT_CHOICES = (
        ('cod', 'Contra reembolso'),
        ('gateway', 'Tarjeta (simulada)'),
    )
    payment_method = forms.ChoiceField(
        label='Método de pago', choices=PAYMENT_CHOICES, widget=forms.RadioSelect, initial='cod'
    )
