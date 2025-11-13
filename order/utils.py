from typing import Any, Dict
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import Order, OrderItem


def send_order_confirmation(order: Order) -> None:
    """Send a confirmation email to the customer with order details.

    Uses templates:
    - order/emails/confirmation.txt
    - order/emails/confirmation.html
    """
    to_email = getattr(order, 'email', None) or ''
    if not to_email:
        return

    # Gather items
    items = list(OrderItem.objects.filter(order=order))
    ctx: Dict[str, Any] = {
        'order': order,
        'items': items,
    }

    subject = f"Confirmación de pedido {getattr(order, 'order_number', order.id)}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')

    text_body = render_to_string('order/emails/confirmation.txt', ctx)
    html_body = render_to_string('order/emails/confirmation.html', ctx)

    msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)
