from decimal import Decimal
from django.conf import settings
from shop.models import Product

class Cart():

    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False, size=None, price=None):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        # Use product_id + size as key to allow same product in different sizes
        cart_key = f"{product_id}_{size}" if size else product_id
        
        if price is None:
            price = product.price
        
        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'quantity': 0,
                'price': str(price),
                'product_id': product_id,
                'size': size
            }
        
        if update_quantity:
            self.cart[cart_key]['quantity'] = quantity
        else:
            self.cart[cart_key]['quantity'] += quantity
        self.save()

    def save(self):
        """
        mark the session as "modified" to make sure it gets saved
        """
        self.session.modified = True

    def remove(self, product, size=None):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id) if hasattr(product, 'id') else str(product)
        # Use product_id + size as key to match add() format
        cart_key = f"{product_id}_{size}" if size else product_id
        
        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()
            
    def clear(self):
        """
        Remove cart from session
        """
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        product_ids = set()
        for key in self.cart.keys():
            # Extract product_id from key (format: "product_id" or "product_id_size")
            product_id = key.split('_')[0]
            product_ids.add(product_id)
        
        # get the product objects and add them to the cart
        products = {str(p.id): p for p in Product.objects.filter(id__in=product_ids)}
        
        for key, item in self.cart.items():
            product_id = item['product_id']
            if product_id in products:
                item['product'] = products[product_id]
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        calculate the total cost of the items in the cart
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        """
        remove cart from session
        """
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()
