from django.db import models
from django.urls import reverse


class Brand(models.Model):
    """Marca del producto."""
    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to='brands/%Y/%m/%d')

    class Meta:
        ordering = ('name',)
        verbose_name = 'brand'
        verbose_name_plural = 'brands'

    def __str__(self) -> str:
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(default='')
    image = models.ImageField(upload_to='categories/%Y/%m/%d', default='')

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])

class Product(models.Model):
    # Relaciones
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='products', on_delete=models.CASCADE, null=True, blank=True, default=None)

    # Atributos principales (obligatorios según modelo conceptual)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # precio_oferta
    gender = models.CharField(max_length=30, default='unisex')  # genero
    color = models.CharField(max_length=50, default='')
    material = models.CharField(max_length=80, default='')
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)  # esta_disponible (mantiene nombre histórico)
    is_featured = models.BooleanField(default=False)  # es_destacado
    created = models.DateTimeField(auto_now_add=True)  # fecha_creacion
    updated = models.DateTimeField(auto_now=True)      # fecha_actualizacion

    # Compatibilidad con plantillas antiguas: mantener campo image
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)

    class Meta:
        ordering = ('name',)
        index_together = (('id', 'slug'),)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])


class ProductImage(models.Model):
    """Imagenes del producto (una puede ser principal)."""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/images/%Y/%m/%d')
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'product image'
        verbose_name_plural = 'product images'

    def __str__(self) -> str:
        return f"Image for {self.product_id}"


class ProductSize(models.Model):
    """TallaProducto: talla y stock por producto."""
    product = models.ForeignKey(Product, related_name='sizes', on_delete=models.CASCADE)
    size = models.CharField(max_length=20)  # talla
    stock = models.PositiveIntegerField()

    class Meta:
        unique_together = (('product', 'size'),)
        verbose_name = 'product size'
        verbose_name_plural = 'product sizes'

    def __str__(self) -> str:
        return f"{self.product_id} - {self.size}"
