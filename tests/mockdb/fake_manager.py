from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Iterator, List, Optional, Type

from django.urls import reverse


# --- Fake model classes (mínimo necesario para vistas y templates) ---

@dataclass
class FakeCategory:
    id: int
    name: str
    slug: str

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('shop:product_list_by_category', args=[self.slug])


@dataclass
class FakeProduct:
    id: int
    name: str
    slug: str
    description: str
    price: Decimal
    available: bool
    category: FakeCategory
    image: Any  # debe tener atributo .url
    # Campos adicionales del modelo real (opcionales en mock)
    offer_price: Decimal = Decimal("0")
    gender: str = "unisex"
    color: str = ""
    material: str = ""
    stock: int = 0
    is_featured: bool = False
    brand: Optional['FakeBrand'] = None

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('shop:product_detail', args=[self.id, self.slug])


@dataclass
class FakeBrand:
    id: int
    name: str
    image: Any

    def __str__(self) -> str:
        return self.name


@dataclass
class FakeProductImage:
    id: int
    product: 'FakeProduct'
    image: Any
    is_primary: bool


@dataclass
class FakeProductSize:
    id: int
    product: 'FakeProduct'
    size: str
    stock: int


@dataclass
class FakeOrderItem:
    id: int
    order: Any  # genérico; no usado por templates
    product: FakeProduct
    price: Decimal
    quantity: int = 1

    def __str__(self) -> str:
        return str(self.id)

    def get_cost(self) -> Decimal:
        return self.price * self.quantity


@dataclass
class FakeOrder:
    id: int
    customer: Optional[FakeCustomer]
    order_number: str
    status: str
    subtotal: Decimal
    taxes: Decimal
    shipping_cost: Decimal
    discount: Decimal
    total: Decimal
    paid: bool = False
    shipping_method: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    address: str = ""
    postal_code: str = ""
    city: str = ""
    payment_method: str = ""
    shipping_address: str = ""
    phone: str = ""

    def __str__(self) -> str:  # pragma: no cover
        return f"Order {self.order_number or self.id}"

    def get_total_cost(self) -> Decimal:
        # Puede ser calculado desde OrderItem externamente si no hay total
        return self.total

    @property
    def items(self):
        """Emula la relación inversa related_name='items' de OrderItem.
        Permite usar order.items.all en plantillas.
        """
        order_self = self

        class _Rel:
            def __init__(self, order):
                self._order = order

            def all(self):
                from order.models import OrderItem as DjangoOrderItem
                return DjangoOrderItem.objects.filter(order=self._order)

        return _Rel(order_self)


@dataclass
class FakeCustomer:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    city: str
    postal_code: str

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class FakeCart:
    id: int
    customer: FakeCustomer


@dataclass
class FakeCartItem:
    id: int
    cart: FakeCart
    product: FakeProduct
    size: str
    quantity: int


@dataclass
class FakeUserAccount:
    id: int
    email: str
    password_hash: str
    role: str
    first_name: str
    last_name: str
    is_active: bool


# --- Fake queryset/manager ---

class FakeQuerySet(Iterable):
    def __init__(self, model_class: Type[Any], items: List[Any]):
        self._model_class = model_class
        self._items: List[Any] = list(items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __len__(self) -> int:  # pragma: no cover
        return len(self._items)

    def all(self) -> 'FakeQuerySet':
        return FakeQuerySet(self._model_class, self._items)

    def filter(self, **kwargs: Any) -> 'FakeQuerySet':
        filtered = [obj for obj in self._items if _matches(obj, kwargs)]
        return FakeQuerySet(self._model_class, filtered)

    def get(self, **kwargs: Any) -> Any:
        matches = [obj for obj in self._items if _matches(obj, kwargs)]
        if not matches:
            # Levanta la excepción del modelo real para compatibilidad con get_object_or_404
            raise self._model_class.DoesNotExist()  # type: ignore[attr-defined]
        if len(matches) > 1:
            raise self._model_class.MultipleObjectsReturned()  # type: ignore[attr-defined]
        return matches[0]

    def first(self) -> Optional[Any]:  # pragma: no cover
        return self._items[0] if self._items else None

    def count(self) -> int:  # pragma: no cover
        return len(self._items)


class FakeManager:
    """Subconjunto pequeño del Manager de Django para tests sin DB.
    Soporta: all(), filter(), get(), create().
    """

    def __init__(self, model_class: Type[Any], initial_items: Optional[List[Any]] = None):
        self._model_class = model_class
        self._items: List[Any] = list(initial_items or [])
        self._next_id = 1 + max((getattr(x, 'id', 0) or 0) for x in self._items) if self._items else 1

    def all(self) -> FakeQuerySet:
        return FakeQuerySet(self._model_class, self._items)

    def filter(self, **kwargs: Any) -> FakeQuerySet:
        return self.all().filter(**kwargs)

    def get(self, **kwargs: Any) -> Any:
        matches = [obj for obj in self._items if _matches(obj, kwargs)]
        if not matches:
            # Levanta la excepción del modelo real para que get_object_or_404 funcione.
            raise self._model_class.DoesNotExist()  # type: ignore[attr-defined]
        if len(matches) > 1:
            raise self._model_class.MultipleObjectsReturned()  # type: ignore[attr-defined]
        return matches[0]

    def create(self, **kwargs: Any) -> Any:
        if 'id' not in kwargs or kwargs['id'] is None:
            kwargs['id'] = self._next_id
            self._next_id += 1
        obj = _construct_fake_for_model(self._model_class, kwargs)
        self._items.append(obj)
        return obj

    def bulk_set(self, items: List[Any]) -> None:
        self._items = list(items)
        self._next_id = 1 + max((getattr(x, 'id', 0) or 0) for x in self._items) if self._items else 1


# --- Helpers ---

def _matches(obj: Any, filters: Dict[str, Any]) -> bool:
    for k, v in filters.items():
        if '__' in k:
            field, op = k.split('__', 1)
            val = getattr(obj, field)
            if op == 'in':
                return any(str(val) == str(x) if field == 'id' else val == x for x in v)
            else:
                return False
        else:
            val = getattr(obj, k)
            if hasattr(val, 'id') and hasattr(v, 'id'):
                if val.id != v.id:
                    return False
            else:
                if val != v:
                    return False
    return True


def _construct_fake_for_model(model_class: Type[Any], kwargs: Dict[str, Any]) -> Any:
    """Crea una instancia de la fake class adecuada para el modelo Django."""
    from shop.models import Category as DjangoCategory, Product as DjangoProduct, Brand as DjangoBrand, ProductImage as DjangoProductImage, ProductSize as DjangoProductSize
    from order.models import Order as DjangoOrder, OrderItem as DjangoOrderItem, Customer as DjangoCustomer
    from cart.models import Cart as DjangoCart, CartItem as DjangoCartItem
    try:
        from accounts.models import UserAccount as DjangoUserAccount
    except Exception:  # pragma: no cover - accounts may not be installed in some contexts
        DjangoUserAccount = None  # type: ignore

    if model_class.__name__ == 'Category' and model_class is DjangoCategory:
        return FakeCategory(id=kwargs['id'], name=kwargs['name'], slug=kwargs['slug'])

    if model_class.__name__ == 'Product' and model_class is DjangoProduct:
        cat = kwargs['category']
        if not isinstance(cat, FakeCategory):
            raise AssertionError('Product.category debe ser FakeCategory en modo mock')
        image = kwargs.get('image')
        if isinstance(image, str):
            image = SimpleNamespace(url=image)
        brand = kwargs.get('brand')
        # brand puede ser None o FakeBrand
        return FakeProduct(
            id=kwargs['id'], name=kwargs['name'], slug=kwargs['slug'],
            description=kwargs.get('description', ''),
            price=Decimal(str(kwargs.get('price', '0'))),
            available=bool(kwargs.get('available', True)),
            category=cat,
            image=image or SimpleNamespace(url=''),
            offer_price=Decimal(str(kwargs.get('offer_price', '0'))),
            gender=str(kwargs.get('gender', 'unisex')),
            color=str(kwargs.get('color', '')),
            material=str(kwargs.get('material', '')),
            stock=int(kwargs.get('stock', 0)),
            is_featured=bool(kwargs.get('is_featured', False)),
            brand=brand if isinstance(brand, FakeBrand) else None,
        )

    if model_class.__name__ == 'Brand' and model_class is DjangoBrand:
        image = kwargs.get('image')
        if isinstance(image, str):
            image = SimpleNamespace(url=image)
        return FakeBrand(id=kwargs['id'], name=kwargs['name'], image=image or SimpleNamespace(url=''))

    if model_class.__name__ == 'ProductImage' and model_class is DjangoProductImage:
        img = kwargs.get('image')
        if isinstance(img, str):
            img = SimpleNamespace(url=img)
        return FakeProductImage(id=kwargs['id'], product=kwargs['product'], image=img or SimpleNamespace(url=''), is_primary=bool(kwargs.get('is_primary', False)))

    if model_class.__name__ == 'ProductSize' and model_class is DjangoProductSize:
        return FakeProductSize(id=kwargs['id'], product=kwargs['product'], size=str(kwargs['size']), stock=int(kwargs.get('stock', 0)))

    if model_class.__name__ == 'OrderItem' and model_class is DjangoOrderItem:
        return FakeOrderItem(
            id=kwargs['id'],
            order=kwargs.get('order'),
            product=kwargs['product'],
            price=Decimal(str(kwargs.get('price', '0'))),
            quantity=int(kwargs.get('quantity', 1))
        )

    if model_class.__name__ == 'Order' and model_class is DjangoOrder:
        cust = kwargs.get('customer')
        if cust is not None and not isinstance(cust, FakeCustomer):
            raise AssertionError('Order.customer debe ser FakeCustomer o None en modo mock')
        return FakeOrder(
            id=kwargs['id'],
            customer=cust,
            order_number=str(kwargs.get('order_number', '')),
            status=str(kwargs.get('status', 'pending')),
            subtotal=Decimal(str(kwargs.get('subtotal', '0'))),
            taxes=Decimal(str(kwargs.get('taxes', '0'))),
            shipping_cost=Decimal(str(kwargs.get('shipping_cost', '0'))),
            discount=Decimal(str(kwargs.get('discount', '0'))),
            total=Decimal(str(kwargs.get('total', '0'))),
            paid=bool(kwargs.get('paid', False)),
            shipping_method=str(kwargs.get('shipping_method', '')),
            first_name=str(kwargs.get('first_name', '')),
            last_name=str(kwargs.get('last_name', '')),
            email=str(kwargs.get('email', '')),
            address=str(kwargs.get('address', '')),
            postal_code=str(kwargs.get('postal_code', '')),
            city=str(kwargs.get('city', '')),
            payment_method=str(kwargs.get('payment_method', '')),
            shipping_address=str(kwargs.get('shipping_address', '')),
            phone=str(kwargs.get('phone', '')),
        )

    if model_class.__name__ == 'Customer' and model_class is DjangoCustomer:
        return FakeCustomer(
            id=kwargs['id'], first_name=kwargs['first_name'], last_name=kwargs['last_name'],
            email=kwargs['email'], phone=kwargs['phone'], address=kwargs['address'],
            city=kwargs['city'], postal_code=kwargs['postal_code']
        )

    if model_class.__name__ == 'Cart' and model_class is DjangoCart:
        return FakeCart(id=kwargs['id'], customer=kwargs['customer'])

    if model_class.__name__ == 'CartItem' and model_class is DjangoCartItem:
        return FakeCartItem(id=kwargs['id'], cart=kwargs['cart'], product=kwargs['product'], size=str(kwargs['size']), quantity=int(kwargs['quantity']))

    if DjangoUserAccount and model_class.__name__ == 'UserAccount' and model_class is DjangoUserAccount:
        return FakeUserAccount(
            id=kwargs['id'],
            email=kwargs['email'],
            password_hash=kwargs.get('password_hash', ''),
            role=kwargs.get('role', 'customer'),
            first_name=kwargs.get('first_name', ''),
            last_name=kwargs.get('last_name', ''),
            is_active=bool(kwargs.get('is_active', True)),
        )

    return SimpleNamespace(**kwargs)