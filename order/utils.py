from typing import Any, Dict, List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import OrderItem
import os

def _mockdb_active():
    return os.environ.get('USE_MOCKDB') == '1' or getattr(settings, 'USE_MOCKDB', False)

def send_order_confirmation(order) -> None:
    """
    Send a confirmation email to the customer. Safe for MockDB mode.
    Uses templates:
      - order/emails/confirmation.txt
      - order/emails/confirmation.html
    """
    to_email = getattr(order, 'email', None) or ''
    if not to_email:
        return

    # Gather items: try ORM first, fallback to fake manager
    items = []
    try:
        items = list(OrderItem.objects.filter(order=order))
    except Exception:
        # Attempt FakeManager fallback
        for oi in getattr(OrderItem.objects, '_items', []):
            if getattr(oi, 'order', None) == order:
                items.append(oi)

    ctx: Dict[str, Any] = {
        'order': order,
        'items': items,
    }

    subject = f"Confirmación de pedido {getattr(order, 'order_number', order.id)}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')

    text_body = render_to_string('order/emails/confirmation.txt', ctx)
    html_body = ''
    try:
        html_body = render_to_string('order/emails/confirmation.html', ctx)
    except Exception:
        html_body = ''

    try:
        msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        # Send non-blocking; fail silently so order flow continues
        msg.send(fail_silently=True)
    except Exception:
        # Do not raise: allow order flow to continue on email failures
        pass
