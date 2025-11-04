from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

from .fake_manager import (
    FakeManager,
    FakeCategory,
    FakeProduct,
    FakeBrand,
    FakeProductImage,
    FakeProductSize,
    FakeCustomer,
    FakeCart,
    FakeCartItem,
)


class MockDB:
    """Parchado de managers de modelos con managers en memoria cargados desde JSON.
    Por defecto, lee fixtures de tests/mockdb/data/*.json
    """

    def __init__(self, data: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self._orig_managers: Dict[Any, Any] = {}
        self._data = data or load_default_data()

    def apply(self) -> None:
        from shop.models import Category, Product, Brand, ProductImage, ProductSize
        from order.models import OrderItem, Customer
        from cart.models import Cart, CartItem

        # Construir objetos en orden para resolver FK
        categories = [_to_fake_category(d) for d in self._data.get('categories', [])]
        categories_by_id = {c.id: c for c in categories}

        brands = [_to_fake_brand(d) for d in self._data.get('brands', [])]
        brands_by_id = {b.id: b for b in brands}

        products = [_to_fake_product(d, categories_by_id, brands_by_id) for d in self._data.get('products', [])]

        product_by_id = {p.id: p for p in products}
        images = [_to_fake_product_image(d, product_by_id) for d in self._data.get('product_images', [])]
        sizes = [_to_fake_product_size(d, product_by_id) for d in self._data.get('product_sizes', [])]

        customers = [_to_fake_customer(d) for d in self._data.get('customers', [])]
        customers_by_id = {c.id: c for c in customers}

        carts = [_to_fake_cart(d, customers_by_id) for d in self._data.get('carts', [])]
        carts_by_id = {c.id: c for c in carts}
        cart_items = [_to_fake_cart_item(d, carts_by_id, product_by_id) for d in self._data.get('cart_items', [])]

        order_items: List[Any] = []

        # Parchear .objects con FakeManager
        self._patch_manager(Category, FakeManager(Category, categories))
        self._patch_manager(Brand, FakeManager(Brand, brands))
        self._patch_manager(Product, FakeManager(Product, products))
        self._patch_manager(ProductImage, FakeManager(ProductImage, images))
        self._patch_manager(ProductSize, FakeManager(ProductSize, sizes))
        self._patch_manager(Customer, FakeManager(Customer, customers))
        self._patch_manager(Cart, FakeManager(Cart, carts))
        self._patch_manager(CartItem, FakeManager(CartItem, cart_items))
        self._patch_manager(OrderItem, FakeManager(OrderItem, order_items))

    def restore(self) -> None:
        for model_class, original in self._orig_managers.items():
            setattr(model_class, 'objects', original)
        self._orig_managers.clear()

    # --- internals ---
    def _patch_manager(self, model_class: Any, fake_manager: FakeManager) -> None:
        if model_class not in self._orig_managers:
            self._orig_managers[model_class] = getattr(model_class, 'objects')
        setattr(model_class, 'objects', fake_manager)

    def _get_manager(self, model_class: Any) -> FakeManager:
        return getattr(model_class, 'objects')  # type: ignore[return-value]


def load_default_data() -> Dict[str, List[Dict[str, Any]]]:
    # --- Determinar ruta base del proyecto ---
    base = Path(settings.BASE_DIR)
    if base.name == "config":  # si BASE_DIR apunta a /config, subimos un nivel
        base = base.parent

    # --- Carpeta donde están los datos mock ---
    data_dir = base / "tests" / "mockdb" / "data"

    def load(name: str) -> List[Dict[str, Any]]:
        p = data_dir / f"{name}.json"
        if not p.exists():
            print(f"[mockdb] ⚠️ No se encontró {p}")
            return []
        print(f"[mockdb] ✅ Cargando {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        print(f"[mockdb]   → {len(data)} elementos cargados.")
        return data

    # --- Cargar datasets ---
    data = {
        "categories": load("categories"),
        "brands": load("brands"),
        "products": load("products"),
        "product_images": load("product_images"),
        "product_sizes": load("product_sizes"),
        "customers": load("customers"),
        "carts": load("carts"),
        "cart_items": load("cart_items"),
        "order_items": load("order_items"),
    }
    print(
        f"[mockdb] Datos cargados: {{ cats: {len(data['categories'])}, brands: {len(data['brands'])}, products: {len(data['products'])}, imgs: {len(data['product_images'])}, sizes: {len(data['product_sizes'])}, customers: {len(data['customers'])}, carts: {len(data['carts'])}, cart_items: {len(data['cart_items'])}, order_items: {len(data['order_items'])} }}"
    )
    return data




def _to_fake_category(d: Dict[str, Any]) -> FakeCategory:
    return FakeCategory(id=int(d['id']), name=d['name'], slug=d['slug'])


def _to_fake_product(d: Dict[str, Any], cats_by_id: Dict[int, FakeCategory], brands_by_id: Dict[int, FakeBrand]) -> FakeProduct:
    cat_id = int(d['category']) if isinstance(d['category'], (int, str)) else d['category']['id']
    cat = cats_by_id[cat_id]
    brand_id = int(d['brand']) if isinstance(d.get('brand'), (int, str)) else (d['brand']['id'] if isinstance(d.get('brand'), dict) else None)
    # El FakeProduct no guarda brand directamente (modelo real sí), pero podemos ignorarlo salvo que se use
    from shop.models import Product
    mgr = FakeManager(Product, [])
    return mgr.create(
        id=int(d['id']),
        name=d['name'],
        slug=d.get('slug', str(d['name']).lower().replace(' ', '-')),
        description=d.get('description', ''),
        price=d.get('price', '0'),
        available=bool(d.get('available', True)),
        category=cat,
        image=d.get('image_url', ''),
    )


def _to_fake_brand(d: Dict[str, Any]) -> FakeBrand:
    from shop.models import Brand
    mgr = FakeManager(Brand, [])
    return mgr.create(id=int(d['id']), name=d['name'], image=d.get('image_url', ''))


def _to_fake_product_image(d: Dict[str, Any], product_by_id: Dict[int, FakeProduct]) -> FakeProductImage:
    from shop.models import ProductImage
    mgr = FakeManager(ProductImage, [])
    product = product_by_id[int(d['product'])]
    return mgr.create(id=int(d['id']), product=product, image=d.get('image_url', ''), is_primary=bool(d.get('is_primary', False)))


def _to_fake_product_size(d: Dict[str, Any], product_by_id: Dict[int, FakeProduct]) -> FakeProductSize:
    from shop.models import ProductSize
    mgr = FakeManager(ProductSize, [])
    product = product_by_id[int(d['product'])]
    return mgr.create(id=int(d['id']), product=product, size=str(d['size']), stock=int(d['stock']))


def _to_fake_customer(d: Dict[str, Any]) -> FakeCustomer:
    from order.models import Customer
    mgr = FakeManager(Customer, [])
    return mgr.create(
        id=int(d['id']), first_name=d['first_name'], last_name=d['last_name'], email=d['email'], phone=d['phone'],
        address=d['address'], city=d['city'], postal_code=d['postal_code'], password=d['password']
    )


def _to_fake_cart(d: Dict[str, Any], customers_by_id: Dict[int, FakeCustomer]) -> FakeCart:
    from cart.models import Cart
    mgr = FakeManager(Cart, [])
    customer = customers_by_id[int(d['customer'])]
    return mgr.create(id=int(d['id']), customer=customer)


def _to_fake_cart_item(d: Dict[str, Any], carts_by_id: Dict[int, FakeCart], product_by_id: Dict[int, FakeProduct]) -> FakeCartItem:
    from cart.models import CartItem
    mgr = FakeManager(CartItem, [])
    cart = carts_by_id[int(d['cart'])]
    product = product_by_id[int(d['product'])]
    return mgr.create(id=int(d['id']), cart=cart, product=product, size=str(d['size']), quantity=int(d['quantity']))