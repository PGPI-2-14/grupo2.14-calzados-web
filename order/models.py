from django.db import models
from shop.models import Product
from accounts.models import UserAccount


class Customer(UserAccount):
    """Cliente del ecommerce que hereda de UserAccount.
    Solo define los atributos adicionales que no existen en UserAccount.
    """
    phone = models.CharField(max_length=30, default='')
    address = models.CharField(max_length=250, default='')
    city = models.CharField(max_length=100, default='')
    postal_code = models.CharField(max_length=20, default='')

    class Meta:
        ordering = ('-created',)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Order(models.Model):
    # Relación con cliente
    customer = models.ForeignKey(Customer, related_name='orders', on_delete=models.CASCADE, null=True, blank=True)

    # Datos originales mantenidos para compatibilidad con formularios actuales
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    email = models.EmailField(default='test@example.com')
    address = models.CharField(max_length=250, default='')
    postal_code = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=100, default='')

    # Nuevos atributos del modelo conceptual
    created = models.DateTimeField(auto_now_add=True)           # fecha_creacion
    updated = models.DateTimeField(auto_now=True)
    order_number = models.CharField(max_length=40, default='')  # numero_pedido
    status = models.CharField(max_length=30, default='pending') # estado
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0)      # impuestos
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # coste_entrega
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, default='') # metodo_pago
    shipping_address = models.CharField(max_length=250, default='') # direccion_envio
    phone = models.CharField(max_length=30, default='')
    paid = models.BooleanField(default=False)
    
    #Braintree atributes
    braintree_id = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return 'Order {}'.format(self.id)

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    # Campos del modelo conceptual
    size = models.CharField(max_length=20, default='')  # talla
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # precio_unitario
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # total

    # Compatibilidad con código existente (cart/order views)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return '{}'.format(self.id)

    def get_cost(self):
        # Mantener comportamiento antiguo; line_total puede calcularse externamente
        return self.price * self.quantity
