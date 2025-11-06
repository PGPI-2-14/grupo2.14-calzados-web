from functools import wraps
from typing import Callable
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse


SESSION_USER_ID = 'mock_user_id'
SESSION_USER_ROLE = 'mock_user_role'


def _require_role(role: str):
    def decorator(view_func: Callable[[HttpRequest], HttpResponse]):
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            r = request.session.get(SESSION_USER_ROLE)
            if r != role:
                # Redirigir a login placeholder mientras no implementamos login
                return HttpResponseRedirect(reverse('accounts:login'))
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def require_admin(view_func: Callable[[HttpRequest], HttpResponse]):
    from accounts.models import UserAccount
    return _require_role(UserAccount.ROLE_ADMIN)(view_func)


def require_customer(view_func: Callable[[HttpRequest], HttpResponse]):
    from accounts.models import UserAccount
    return _require_role(UserAccount.ROLE_CUSTOMER)(view_func)
