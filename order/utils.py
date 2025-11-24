from typing import Any, Dict, List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from .models import OrderItem
import os

def _mockdb_active():
    return os.environ.get('USE_MOCKDB') == '1' or getattr(settings, 'USE_MOCKDB', False)

def send_order_confirmation(order) -> bool:
    """
    Send a confirmation email to the customer.
    Returns True if email was sent successfully, False otherwise.
    Works with or without SendGrid configuration.
    """
    to_email = getattr(order, 'email', None) or ''
    if not to_email:
        print("[order/utils] No email address found for order")
        return False

    # Gather items
    items = []
    try:
        items = list(OrderItem.objects.filter(order=order))
    except Exception:
        # Fallback for MockDB
        for oi in getattr(OrderItem.objects, '_items', []):
            if getattr(oi, 'order', None) == order:
                items.append(oi)

    # Prepare context
    ctx: Dict[str, Any] = {
        'order': order,
        'items': items,
        'order_number': getattr(order, 'order_number', f'#{order.id}'),
        'customer_name': f"{getattr(order, 'first_name', '')} {getattr(order, 'last_name', '')}",
        'total': getattr(order, 'total', 0),
        'subtotal': getattr(order, 'subtotal', 0),
        'shipping_cost': getattr(order, 'shipping_cost', 0),
    }

    subject = f"Confirmación de pedido {ctx['order_number']} - Nexo Shoes"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nexoshoes.com')

    # Create simple text message (works without templates)
    text_body = f"""
Hola {ctx['customer_name']},

¡Gracias por tu pedido en Nexo Shoes!

Número de pedido: {ctx['order_number']}
Total: {ctx['total']}€

Detalles del pedido:
"""
    for item in items:
        product_name = getattr(getattr(item, 'product', None), 'name', 'Producto')
        quantity = getattr(item, 'quantity', 1)
        price = getattr(item, 'price', 0)
        text_body += f"- {product_name} x{quantity} = {float(price) * quantity}€\n"
    
    text_body += f"""
Subtotal: {ctx['subtotal']}€
Envío: {ctx['shipping_cost']}€
Total: {ctx['total']}€

Gracias por tu compra.
Nexo Shoes
"""

    # Try to render HTML template if available
    html_body = ''
    try:
        html_body = render_to_string('order/emails/confirmation.html', ctx)
    except Exception as e:
        print(f"[order/utils] Could not render HTML template: {e}")

    # Send email
    try:
        if html_body:
            msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
        else:
            send_mail(subject, text_body, from_email, [to_email], fail_silently=False)
        
        print(f"[order/utils] ✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"[order/utils] ❌ Failed to send email: {e}")
        # In development without proper email config, this is expected
        if getattr(settings, 'DEBUG', False):
            print(f"[order/utils] ℹ️ Email content printed above (check console)")
        return False


def generate_order_ticket_text(order) -> str:
    """
    Generate a text-format ticket for the order that can be downloaded.
    """
    # Gather items
    items = []
    try:
        items = list(OrderItem.objects.filter(order=order))
    except Exception:
        for oi in getattr(OrderItem.objects, '_items', []):
            if getattr(oi, 'order', None) == order:
                items.append(oi)
    
    lines = []
    lines.append("=" * 60)
    lines.append("           NEXO SHOES - TICKET DE COMPRA")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Numero de pedido: {getattr(order, 'order_number', order.id)}")
    
    # Format date if available
    created = getattr(order, 'created', None)
    if created:
        try:
            from datetime import datetime
            if hasattr(created, 'strftime'):
                lines.append(f"Fecha: {created.strftime('%d/%m/%Y %H:%M')}")
            else:
                lines.append(f"Fecha: {created}")
        except:
            lines.append(f"Fecha: {created}")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("DATOS DEL CLIENTE")
    lines.append("-" * 60)
    lines.append(f"Nombre: {getattr(order, 'first_name', '')} {getattr(order, 'last_name', '')}")
    lines.append(f"Email: {getattr(order, 'email', '')}")
    lines.append(f"Telefono: {getattr(order, 'phone', 'N/A')}")
    
    if getattr(order, 'shipping_method', '') == 'home':
        lines.append(f"Direccion: {getattr(order, 'address', '')}")
        lines.append(f"Ciudad: {getattr(order, 'city', '')} - CP: {getattr(order, 'postal_code', '')}")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("ARTICULOS")
    lines.append("-" * 60)
    
    for item in items:
        product_name = getattr(getattr(item, 'product', None), 'name', 'Producto')
        quantity = getattr(item, 'quantity', 1)
        price = getattr(item, 'price', 0)
        size = getattr(item, 'size', '')
        
        size_text = f" (Talla: {size})" if size else ""
        lines.append(f"{product_name}{size_text}")
        lines.append(f"  Cantidad: {quantity} x {price}€ = {float(price) * quantity:.2f}€")
        lines.append("")
    
    lines.append("-" * 60)
    lines.append("RESUMEN")
    lines.append("-" * 60)
    lines.append(f"Subtotal: {getattr(order, 'subtotal', 0)}€")
    lines.append(f"Envio: {getattr(order, 'shipping_cost', 0)}€")
    lines.append(f"TOTAL: {getattr(order, 'total', 0)}€")
    lines.append("")
    
    # Payment and shipping info
    payment_method = getattr(order, 'payment_method', 'N/A')
    payment_display = {
        'card': 'Tarjeta',
        'cod': 'Contrareembolso',
        'gateway': 'Pasarela de pago'
    }.get(payment_method, payment_method)
    
    shipping_method = getattr(order, 'shipping_method', 'N/A')
    shipping_display = {
        'home': 'Envio a domicilio',
        'store': 'Recogida en tienda'
    }.get(shipping_method, shipping_method)
    
    lines.append(f"Metodo de pago: {payment_display}")
    lines.append(f"Metodo de envio: {shipping_display}")
    lines.append(f"Estado del pago: {'Pagado' if getattr(order, 'paid', False) else 'Pendiente'}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("         Gracias por tu compra en Nexo Shoes")
    lines.append("           www.nexoshoes.com")
    lines.append("=" * 60)
    
    return "\n".join(lines)
