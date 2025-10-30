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
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```