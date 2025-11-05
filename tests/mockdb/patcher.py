from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

from .fake_manager import FakeManager, FakeCategory, FakeProduct


class MockDB:
    """Parchado de managers de modelos con managers en memoria cargados desde JSON.
    Por defecto, lee fixtures de tests/mockdb/data/*.json
    """

    def __init__(self, data: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self._orig_managers: Dict[Any, Any] = {}
        self._data = data or load_default_data()

    def apply(self) -> None:
        from shop.models import Category, Product
        from order.models import OrderItem

        # Construir objetos en orden para resolver FK
        categories = [_to_fake_category(d) for d in self._data.get('categories', [])]
        categories_by_id = {c.id: c for c in categories}

        products = [_to_fake_product(d, categories_by_id) for d in self._data.get('products', [])]
        order_items: List[Any] = []

        # Parchear .objects con FakeManager
        self._patch_manager(Category, FakeManager(Category, categories))
        self._patch_manager(Product, FakeManager(Product, products))
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
        "products": load("products"),
        "order_items": load("order_items"),
    }
    print(f"[mockdb] Datos cargados: {{ categories: {len(data['categories'])}, products: {len(data['products'])}, order_items: {len(data['order_items'])} }}")
    return data




def _to_fake_category(d: Dict[str, Any]) -> FakeCategory:
    return FakeCategory(id=int(d['id']), name=d['name'], slug=d['slug'])


def _to_fake_product(d: Dict[str, Any], cats_by_id: Dict[int, FakeCategory]) -> FakeProduct:
    cat_id = int(d['category']) if isinstance(d['category'], (int, str)) else d['category']['id']
    cat = cats_by_id[cat_id]
    from shop.models import Product
    mgr = FakeManager(Product, [])
    return mgr.create(
        id=int(d['id']),
        name=d['name'],
        slug=d['slug'],
        description=d.get('description', ''),
        price=d.get('price', '0'),
        available=bool(d.get('available', True)),
        category=cat,
        image=d.get('image_url', ''),
    )