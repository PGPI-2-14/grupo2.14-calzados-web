## Instalación

**1.Clonar repositorio e instalar paquetes**
```sh
git clone https://github.com/isasancas/grupo2.14-calzados-web.git
pip install -r requirements.txt
```
**2.Configurar Virtualenv**
```sh
python -m venv venv
venv\Scripts\activate
```
**3.Migrar y arrancar servidor**
```sh
./run_mockdb.ps1
```

### Guía rápida para probar lo desarrollado (admin-lite)

1) Arranca la app en modo MockDB (activa DEBUG y USE_MOCKDB):

```sh
./run_mockdb.ps1
```

2) Inicia sesión de admin de depuración (solo en MockDB):

- /accounts/debug/login-admin/

3) Páginas a revisar (admin-lite):

- Resumen de ventas (métricas con pedidos de ejemplo):
	- /accounts/admin-lite/sales/
- Pedidos — listado con filtro por estado:
	- /accounts/admin-lite/orders/
- Pedidos — detalle (cambia el ID por el que quieras):
	- /accounts/admin-lite/orders/1/
- Productos — alta, edición y borrado:
	- /accounts/admin-lite/products/

4) Checkout (mock) — entrega y pago:

- Entrega (forma de envío, datos de entrega y estimación de costes):
	- /accounts/admin-lite/checkout/delivery/
- Pago (selección de método y confirmación):
	- /accounts/admin-lite/checkout/payment/

Notas del checkout mock:
- Envío gratis a partir de 50€ en envío a domicilio (configurable en `tests/mockdb/data/shipping.json`).
- Si eliges "Contra reembolso", el pedido se crea aceptado (estado `processing`) y no se marca como pagado.
- Este flujo es exclusivo del área admin-lite para pruebas; el frontend público no se ha modificado.