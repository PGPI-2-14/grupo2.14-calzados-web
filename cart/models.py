from django.db import models
from shop.models import Product
from order.models import Customer


class Cart(models.Model):
    customer = models.ForeignKey(Customer, related_name='carts', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Cart {self.id} for {self.customer_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='cart_items', on_delete=models.CASCADE)
    size = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"Item {self.id} in cart {self.cart_id}"
