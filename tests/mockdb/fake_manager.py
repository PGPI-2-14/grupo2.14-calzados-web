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

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('shop:product_detail', args=[self.id, self.slug])


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
    from shop.models import Category as DjangoCategory, Product as DjangoProduct
    from order.models import OrderItem as DjangoOrderItem

    if model_class.__name__ == 'Category' and model_class is DjangoCategory:
        return FakeCategory(id=kwargs['id'], name=kwargs['name'], slug=kwargs['slug'])

    if model_class.__name__ == 'Product' and model_class is DjangoProduct:
        cat = kwargs['category']
        if not isinstance(cat, FakeCategory):
            raise AssertionError('Product.category debe ser FakeCategory en modo mock')
        image = kwargs.get('image')
        if isinstance(image, str):
            image = SimpleNamespace(url=image)
        return FakeProduct(
            id=kwargs['id'], name=kwargs['name'], slug=kwargs['slug'],
            description=kwargs.get('description', ''),
            price=Decimal(str(kwargs.get('price', '0'))),
            available=bool(kwargs.get('available', True)),
            category=cat,
            image=image or SimpleNamespace(url='')
        )

    if model_class.__name__ == 'OrderItem' and model_class is DjangoOrderItem:
        return FakeOrderItem(
            id=kwargs['id'],
            order=kwargs.get('order'),
            product=kwargs['product'],
            price=Decimal(str(kwargs.get('price', '0'))),
            quantity=int(kwargs.get('quantity', 1))
        )

    return SimpleNamespace(**kwargs)