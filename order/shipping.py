from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from django.conf import settings


@dataclass
class ShippingMethod:
    code: str
    name: str
    price: float


@dataclass
class ShippingConfig:
    free_shipping_threshold: float
    methods: List[ShippingMethod]


_DEFAULT_CONFIG = ShippingConfig(
    free_shipping_threshold=50.0,
    methods=[
        ShippingMethod(code="home", name="Envío a domicilio", price=4.99),
        ShippingMethod(code="store", name="Recogida en tienda", price=0.0),
    ],
)


def _project_root() -> Path:
    base = Path(settings.BASE_DIR)
    return base.parent if base.name == "config" else base


def load_config() -> ShippingConfig:
    try:
        data_path = _project_root() / "tests" / "mockdb" / "data" / "shipping.json"
        if data_path.exists():
            data = json.loads(data_path.read_text(encoding="utf-8"))
            threshold = float(data.get("free_shipping_threshold", 50.0))
            methods = [
                ShippingMethod(code=m["code"], name=m["name"], price=float(m.get("price", 0)))
                for m in data.get("methods", [])
            ]
            if methods:
                return ShippingConfig(free_shipping_threshold=threshold, methods=methods)
    except Exception:
        pass
    return _DEFAULT_CONFIG


def method_choices() -> List[Tuple[str, str]]:
    return [(m.code, m.name) for m in load_config().methods]


def compute_shipping(subtotal: float, method_code: str) -> float:
    cfg = load_config()
    # Buscar método
    m: Optional[ShippingMethod] = next((x for x in cfg.methods if x.code == method_code), None)
    if m is None:
        # Fallback al primero
        m = cfg.methods[0]
    # Envío gratuito si supera el umbral y el método es a domicilio
    if method_code == "home" and subtotal >= cfg.free_shipping_threshold:
        return 0.0
    return float(m.price)


def method_name(method_code: str) -> str:
    """Devuelve el nombre legible del método de envío para mostrar en UI."""
    cfg = load_config()
    m = next((x for x in cfg.methods if x.code == method_code), None)
    return m.name if m else method_code
