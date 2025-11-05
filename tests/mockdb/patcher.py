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
    FakeUserAccount,
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
        from order.models import Order, OrderItem, Customer
        from cart.models import Cart, CartItem
        try:
            from accounts.models import UserAccount
        except Exception:
            UserAccount = None  # type: ignore

        # Construir objetos en orden para resolver FK
        categories = [_to_fake_category(d) for d in self._data.get('categories', [])]
        categories_by_id = {c.id: c for c in categories}

        brands = [_to_fake_brand(d) for d in self._data.get('brands', [])]
        brands_by_id = {b.id: b for b in brands}

        products = [_to_fake_product(d, categories_by_id, brands_by_id) for d in self._data.get('products', [])]

        product_by_id = {p.id: p for p in products}
        images = [_to_fake_product_image(d, product_by_id) for d in self._data.get('product_images', [])]
        sizes = [_to_fake_product_size(d, product_by_id) for d in self._data.get('product_sizes', [])]

        # Datos de clientes y admins según nueva estructura
        customers_data = self._data.get('customer') or self._data.get('customers') or []
        admins_data = self._data.get('admin') or []

        customers: List[Any] = [_to_fake_customer(d) for d in customers_data]
        customers_by_id = {c.id: c for c in customers}

        # Construir cuentas de usuario: admins + clientes
        users: List[Any] = []
        if UserAccount:
            users.extend([_to_fake_user(d) for d in admins_data])
            users.extend([_to_fake_user_from_customer(d) for d in customers_data])
        users_by_id = {u.id: u for u in users} if users else {}

        carts = [_to_fake_cart(d, customers_by_id) for d in self._data.get('carts', [])]
        carts_by_id = {c.id: c for c in carts}
        cart_items = [_to_fake_cart_item(d, carts_by_id, product_by_id) for d in self._data.get('cart_items', [])]

        # Construcción de pedidos y líneas
        orders_data = self._data.get('orders', [])
        orders: List[Any] = []
        if orders_data:
            orders = [_to_fake_order(d, customers_by_id) for d in orders_data]
        else:
            # Si no hay orders.json, generar un pedido por defecto si hay order_items
            if self._data.get('order_items'):
                from decimal import Decimal
                from order.models import Order as DjangoOrder
                omgr = FakeManager(DjangoOrder, [])
                default_customer = customers[0] if customers else None
                orders.append(omgr.create(
                    id=1,
                    customer=default_customer,
                    order_number='MOCK-0001',
                    status='pending',
                    subtotal='0', taxes='0', shipping_cost='0', discount='0', total='0', paid=False,
                    first_name=getattr(default_customer, 'first_name', ''),
                    last_name=getattr(default_customer, 'last_name', ''),
                    email=getattr(default_customer, 'email', ''),
                    address=getattr(default_customer, 'address', ''),
                    postal_code=getattr(default_customer, 'postal_code', ''),
                    city=getattr(default_customer, 'city', ''),
                ))

        orders_by_id = {o.id: o for o in orders}

        order_items: List[Any] = []
        if self._data.get('order_items'):
            order_items = [_to_fake_order_item(d, orders_by_id, product_by_id) for d in self._data.get('order_items', [])]
            # Recalcular totales básicos por pedido si no vienen dados
            from decimal import Decimal
            totals: Dict[int, Decimal] = {}
            for it in order_items:
                oid = getattr(getattr(it, 'order', None), 'id', None)
                if oid is None:
                    # Asignar al primer pedido si existe
                    if orders:
                        it.order = orders[0]
                        oid = orders[0].id
                if oid is None:
                    continue
                totals[oid] = totals.get(oid, Decimal('0')) + (it.price * it.quantity)
            for o in orders:
                if getattr(o, 'total', None) in (None, 0, '0'):
                    total = totals.get(o.id)
                    if total is not None:
                        o.subtotal = total
                        o.total = total

        # Parchear .objects con FakeManager
        self._patch_manager(Category, FakeManager(Category, categories))
        self._patch_manager(Brand, FakeManager(Brand, brands))
        self._patch_manager(Product, FakeManager(Product, products))
        self._patch_manager(ProductImage, FakeManager(ProductImage, images))
        self._patch_manager(ProductSize, FakeManager(ProductSize, sizes))
        self._patch_manager(Customer, FakeManager(Customer, customers))
        self._patch_manager(Order, FakeManager(Order, orders))
        self._patch_manager(Cart, FakeManager(Cart, carts))
        self._patch_manager(CartItem, FakeManager(CartItem, cart_items))
        self._patch_manager(OrderItem, FakeManager(OrderItem, order_items))
        if UserAccount:
            self._patch_manager(UserAccount, FakeManager(UserAccount, users))

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


def save_products_to_fixture() -> None:
    """Vuelca el estado actual de Product.objects a tests/mockdb/data/products.json.
    Útil para persistir cambios del admin-lite entre reinicios en desarrollo.
    """
    from shop.models import Product

    # Reutilizar la lógica de rutas usada por load_default_data
    base = Path(settings.BASE_DIR)
    if base.name == "config":
        base = base.parent
    data_dir = base / "tests" / "mockdb" / "data"
    path = data_dir / "products.json"

    def to_dict(p: Any) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": int(getattr(p, 'id', 0) or 0),
            "category": int(getattr(getattr(p, 'category', None), 'id', 0) or 0),
            "name": getattr(p, 'name', ''),
            "slug": getattr(p, 'slug', ''),
            "description": getattr(p, 'description', ''),
            "image_url": getattr(getattr(p, 'image', None), 'url', ''),
            "price": str(getattr(p, 'price', '0')),
            "available": bool(getattr(p, 'available', True)),
            "offer_price": str(getattr(p, 'offer_price', '0')),
            "gender": getattr(p, 'gender', 'unisex'),
            "color": getattr(p, 'color', ''),
            "material": getattr(p, 'material', ''),
            "stock": int(getattr(p, 'stock', 0) or 0),
            "is_featured": bool(getattr(p, 'is_featured', False)),
        }
        brand = getattr(p, 'brand', None)
        if getattr(brand, 'id', None):
            d["brand"] = int(brand.id)
        return d

    items = [to_dict(p) for p in Product.objects.all()]
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[mockdb] 💾 Guardados {len(items)} productos en {path}")


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
        # Nueva estructura: admin.json y customer.json
        "admin": load("admin"),
        "customers": load("customers"),
        # Compatibilidad opcional con ficheros antiguos
        "carts": load("carts"),
        "cart_items": load("cart_items"),
        "order_items": load("order_items"),
        "orders": load("orders"),
        # "users": load("users"),  # deprecado
    }
    print(
        f"[mockdb] Datos cargados: {{ cats: {len(data['categories'])}, brands: {len(data['brands'])}, products: {len(data['products'])}, imgs: {len(data['product_images'])}, sizes: {len(data['product_sizes'])}, admin: {len(data['admin'])}, customers: {len(data['customers'])}, carts: {len(data['carts'])}, cart_items: {len(data['cart_items'])}, order_items: {len(data['order_items'])} }}"
    )
    return data




def _to_fake_category(d: Dict[str, Any]) -> FakeCategory:
    return FakeCategory(id=int(d['id']), name=d['name'], slug=d['slug'])


def _to_fake_product(d: Dict[str, Any], cats_by_id: Dict[int, FakeCategory], brands_by_id: Dict[int, FakeBrand]) -> FakeProduct:
    cat_id = int(d['category']) if isinstance(d['category'], (int, str)) else d['category']['id']
    cat = cats_by_id[cat_id]
    brand_id = int(d['brand']) if isinstance(d.get('brand'), (int, str)) else (d['brand']['id'] if isinstance(d.get('brand'), dict) else None)
    brand = brands_by_id.get(brand_id) if brand_id else None
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
        brand=brand,
        offer_price=d.get('offer_price', '0'),
        gender=d.get('gender', 'unisex'),
        color=d.get('color', ''),
        material=d.get('material', ''),
        stock=d.get('stock', 0),
        is_featured=bool(d.get('is_featured', False)),
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


def _to_fake_order(d: Dict[str, Any], customers_by_id: Dict[int, FakeCustomer]):
    from order.models import Order
    mgr = FakeManager(Order, [])
    customer = None
    if d.get('customer') is not None:
        customer = customers_by_id.get(int(d['customer']))
    return mgr.create(
        id=int(d['id']),
        customer=customer,
        order_number=d.get('order_number', ''),
        status=d.get('status', 'pending'),
        subtotal=d.get('subtotal', '0'),
        taxes=d.get('taxes', '0'),
        shipping_cost=d.get('shipping_cost', '0'),
        discount=d.get('discount', '0'),
        total=d.get('total', '0'),
        paid=bool(d.get('paid', False)),
        first_name=d.get('first_name', ''),
        last_name=d.get('last_name', ''),
        email=d.get('email', ''),
        address=d.get('address', ''),
        postal_code=d.get('postal_code', ''),
        city=d.get('city', ''),
        payment_method=d.get('payment_method', ''),
        shipping_address=d.get('shipping_address', ''),
        phone=d.get('phone', ''),
    )


def _to_fake_order_item(d: Dict[str, Any], orders_by_id: Dict[int, Any], product_by_id: Dict[int, FakeProduct]):
    from order.models import OrderItem
    mgr = FakeManager(OrderItem, [])
    order = None
    if d.get('order') is not None:
        order = orders_by_id.get(int(d['order']))
    product = product_by_id[int(d['product'])]
    return mgr.create(
        id=int(d['id']),
        order=order,
        product=product,
        price=d.get('price', '0'),
        quantity=int(d.get('quantity', 1))
    )


def _to_fake_user(d: Dict[str, Any]) -> FakeUserAccount:
    from accounts.models import UserAccount
    mgr = FakeManager(UserAccount, [])
    return mgr.create(
        id=int(d['id']),
        email=d['email'],
        password_hash=d.get('password_hash', ''),
        role=d.get('role', 'admin'),
        first_name=d.get('first_name', ''),
        last_name=d.get('last_name', ''),
        is_active=bool(d.get('is_active', True)),
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


def _to_fake_customer_from_user(u: Dict[str, Any]) -> FakeCustomer:
    """Construye un FakeCustomer a partir de una entrada de customer.json."""
    from order.models import Customer
    mgr = FakeManager(Customer, [])
    cid = int(u['id']) if 'id' in u else None
    return mgr.create(
        id=cid,
        first_name=u.get('first_name', ''),
        last_name=u.get('last_name', ''),
        email=u.get('email', ''),
        phone=u.get('phone', ''),
        address=u.get('address', ''),
        city=u.get('city', ''),
        postal_code=u.get('postal_code', ''),
        password=u.get('password', ''),
    )


def _to_fake_user_from_customer(u: Dict[str, Any]) -> FakeUserAccount:
    """Crea un UserAccount (rol=customer) a partir de los datos de customer.json."""
    from accounts.models import UserAccount
    mgr = FakeManager(UserAccount, [])
    return mgr.create(
        id=int(u['id']) if 'id' in u else None,
        email=u.get('email', ''),
        password_hash=u.get('password_hash', ''),
        role='customer',
        first_name=u.get('first_name', ''),
        last_name=u.get('last_name', ''),
        is_active=bool(u.get('is_active', True)),
    )