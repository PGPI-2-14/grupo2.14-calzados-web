from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings

from .utils import require_admin, SESSION_USER_ROLE, SESSION_USER_ID
from .models import UserAccount


def login_view(request: HttpRequest) -> HttpResponse:
    # Placeholder: vista de login no implementada aún
    return render(request, 'accounts/login.html')


def register_view(request: HttpRequest) -> HttpResponse:
    # Placeholder: vista de registro no implementada aún
    return render(request, 'accounts/register.html')


@require_admin
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    # Placeholder: panel admin-lite
    return render(request, 'accounts/admin/dashboard.html')


# --- Endpoints temporales de depuración ---
def debug_login_admin(request: HttpRequest) -> HttpResponse:
    """Fija en sesión el rol ADMIN para poder probar el admin-lite sin login."""
    # Seguridad: solo permitir en desarrollo + MockDB
    if not (getattr(settings, "DEBUG", False) and getattr(settings, "USE_MOCKDB", False)):
        return HttpResponseNotFound()
    request.session[SESSION_USER_ROLE] = UserAccount.ROLE_ADMIN
    # Opcional: asociar un id de usuario mock conocido (si existiera). No es requerido por ahora.
    request.session[SESSION_USER_ID] = 1
    return redirect(reverse('accounts:admin_products'))


def debug_logout(request: HttpRequest) -> HttpResponse:
    """Elimina claves de la sesión mock y redirige a login placeholder."""
    # Seguridad: solo permitir en desarrollo + MockDB
    if not (getattr(settings, "DEBUG", False) and getattr(settings, "USE_MOCKDB", False)):
        return HttpResponseNotFound()
    request.session.pop(SESSION_USER_ROLE, None)
    request.session.pop(SESSION_USER_ID, None)
    return redirect(reverse('accounts:login'))
