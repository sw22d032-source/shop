import uuid

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F as models_F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from store_app.models import Product
from . import qpay
from .models import TAX_RATE, Cart, CartItem, Order, OrderItem


# ---------------------------------------------------------------------------
# Туслах функцууд
# ---------------------------------------------------------------------------

def _cart_id(request):
    """Сагсны ID-г session дотор хадгална.

    Session-ий key нь login хийх үед солигддог тул түүнийг сагсны ID болгон
    ашиглавал нэвтрэхэд сагс хоосордог. Харин session доторх утга login
    хийхэд хадгалагдаж үлддэг.
    """
    cart_id = request.session.get('cart_id')
    if not cart_id:
        cart_id = uuid.uuid4().hex
        request.session['cart_id'] = cart_id
    return cart_id


def get_cart(request, create=False):
    """Одоогийн хэрэглэгчийн сагсыг буцаана (байхгүй бол None)."""
    cart_id = request.session.get('cart_id')
    if cart_id:
        cart = Cart.objects.filter(cart_id=cart_id).first()
        if cart:
            return cart
    if create:
        return Cart.objects.create(cart_id=_cart_id(request))
    return None


def cart_summary(cart):
    """Сагсны бараа, тоо, дүн, татварыг тооцоолно."""
    items = []
    if cart:
        items = list(
            CartItem.objects.filter(cart=cart, is_active=True)
            .select_related('product', 'product__category')
            .order_by('id')
        )
    total = sum(item.sub_total() for item in items)
    quantity = sum(item.quantity for item in items)
    tax = round(total * TAX_RATE)
    return {
        'cart_items': items,
        'total': total,
        'quantity': quantity,
        'tax': tax,
        'grand_total': total + tax,
    }


# ---------------------------------------------------------------------------
# Сагс
# ---------------------------------------------------------------------------

def cart(request):
    context = cart_summary(get_cart(request))
    return render(request, 'cart.html', context)


def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.is_available or product.stock <= 0:
        messages.error(request, f'"{product.product_name}" барааны үлдэгдэл дууссан байна.')
        return redirect('cart')

    cart = get_cart(request, create=True)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()

    if cart_item:
        if cart_item.quantity >= product.stock:
            messages.warning(
                request,
                f'"{product.product_name}" барааны үлдэгдэл {product.stock} ширхэг тул дахин нэмэх боломжгүй.')
            return redirect('cart')
        cart_item.quantity += 1
        cart_item.is_active = True
        cart_item.save()
    else:
        CartItem.objects.create(cart=cart, product=product, quantity=1)

    messages.success(request, f'"{product.product_name}" сагсанд нэмэгдлээ.')
    return redirect('cart')


def reduce_cart_item(request, product_id):
    cart = get_cart(request)
    if cart:
        cart_item = CartItem.objects.filter(
            cart=cart, product_id=product_id).first()
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
    return redirect('cart')


def remove_cart_item(request, product_id):
    cart = get_cart(request)
    if cart:
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    return redirect('cart')


# ---------------------------------------------------------------------------
# Захиалга
# ---------------------------------------------------------------------------

def _new_order_number():
    return timezone.now().strftime('%Y%m%d') + uuid.uuid4().hex[:6].upper()


@login_required
def checkout(request):
    cart = get_cart(request)
    summary = cart_summary(cart)

    if not summary['cart_items']:
        messages.warning(request, 'Таны сагс хоосон байна.')
        return redirect('store')

    user = request.user
    account = getattr(user, 'account', None)
    form_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'phone': account.phone_number if account else '',
        'city': '',
        'address': '',
        'note': '',
    }

    if request.method == 'POST':
        for key in form_data:
            form_data[key] = request.POST.get(key, '').strip()

        required = ['first_name', 'last_name', 'email', 'phone', 'city', 'address']
        if any(not form_data[key] for key in required):
            messages.error(request, 'Одоор (*) тэмдэглэсэн бүх талбарыг бөглөнө үү.')
        else:
            with transaction.atomic():
                # Үлдэгдлийг дахин шалгана (өөр хүн худалдаж авсан байж магадгүй)
                products = {}
                for item in summary['cart_items']:
                    product = Product.objects.select_for_update().get(id=item.product_id)
                    if item.quantity > product.stock:
                        messages.error(
                            request,
                            f'"{product.product_name}" барааны үлдэгдэл {product.stock} ширхэг болж өөрчлөгдсөн. Сагсаа шинэчилнэ үү.')
                        return redirect('cart')
                    products[product.id] = product

                order = Order.objects.create(
                    user=user,
                    order_number=_new_order_number(),
                    order_total=summary['total'],
                    tax=summary['tax'],
                    grand_total=summary['grand_total'],
                    **form_data,
                )
                for item in summary['cart_items']:
                    product = products[item.product_id]
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.product_name,
                        price=product.price,
                        quantity=item.quantity,
                    )
                    product.stock -= item.quantity
                    product.save(update_fields=['stock'])

                CartItem.objects.filter(cart=cart).delete()

            # QPay нэхэмжлэх үүсгээд төлбөрийн хуудас руу
            _create_qpay_invoice(request, order)
            return redirect('qpay_pay', order_number=order.order_number)

    context = {**summary, 'form': form_data}
    return render(request, 'place-order.html', context)


@login_required
def order_complete(request, order_number):
    order = get_object_or_404(
        Order, order_number=order_number, user=request.user)
    if order.payment_status == 'pending':
        return redirect('qpay_pay', order_number=order.order_number)
    return render(request, 'order_complete.html', {'order': order})


# ---------------------------------------------------------------------------
# QPay төлбөр
# ---------------------------------------------------------------------------

def _create_qpay_invoice(request, order):
    """Захиалгад QPay нэхэмжлэх үүсгэнэ. Алдаа гарвал мессеж харуулаад False."""
    callback = request.build_absolute_uri(
        reverse('qpay_callback', args=[order.order_number]))
    if settings.QPAY_CALLBACK_BASE:
        callback = settings.QPAY_CALLBACK_BASE.rstrip('/') + reverse('qpay_callback', args=[order.order_number])
    try:
        inv = qpay.create_invoice(order.order_number, order.grand_total,
                                  f'BlueCart захиалга #{order.order_number}', callback)
    except qpay.QPayError as e:
        messages.error(request, f'QPay нэхэмжлэх үүсгэж чадсангүй: {e}')
        return False
    order.qpay_invoice_id = inv['invoice_id']
    order.qpay_qr_text = inv['qr_text']
    order.qpay_qr_image = inv['qr_image']
    order.qpay_short_url = inv['short_url']
    order.qpay_urls = inv['urls']
    order.save(update_fields=['qpay_invoice_id', 'qpay_qr_text', 'qpay_qr_image',
                              'qpay_short_url', 'qpay_urls'])
    return True


def _mark_paid(order, amount):
    """Төлөгдсөн дүн хүрэлцэхүйц бол захиалгыг төлөгдсөн болгоно."""
    if order.payment_status == 'paid':
        return True
    if amount + 0.5 >= order.grand_total:
        Order.objects.filter(id=order.id, payment_status='pending').update(
            payment_status='paid', paid_amount=int(amount), paid_at=timezone.now(), status='Accepted')
        order.refresh_from_db()
        return order.payment_status == 'paid'
    return False


def _refresh_payment(order):
    """QPay-аас төлбөрийн төлөвийг асууна. Буцаах: (paid, error)"""
    if order.payment_status != 'pending' or not order.qpay_invoice_id:
        return order.payment_status == 'paid', None
    try:
        amount = qpay.check_payment(order.qpay_invoice_id)
    except qpay.QPayError as e:
        return False, str(e)
    return _mark_paid(order, amount), None


def _test_button_enabled():
    """Sandbox-ын тест товч: QPAY_TEST_BUTTON тохиргоо, хоосон бол DEBUG."""
    flag = getattr(settings, 'QPAY_TEST_BUTTON', None)
    if flag is None:
        flag = settings.DEBUG
    return bool(flag) and qpay.is_sandbox()


@login_required
def qpay_pay(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status == 'paid':
        return redirect('order_complete', order_number=order.order_number)
    if order.payment_status == 'cancelled':
        messages.info(request, 'Энэ захиалга цуцлагдсан байна.')
        return redirect('dashboard')

    if request.method == 'POST' and request.POST.get('action') == 'retry':
        if _create_qpay_invoice(request, order):
            return redirect('qpay_pay', order_number=order.order_number)

    return render(request, 'qpay_pay.html', {
        'order': order,
        'dev_simulate': _test_button_enabled(),
    })


@login_required
def qpay_check(request, order_number):
    """Төлбөрийн хуудас 3 секунд тутам асуудаг JSON endpoint."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    paid, error = _refresh_payment(order)
    if paid:
        messages.success(request, 'Төлбөр амжилттай төлөгдлөө!')
    return JsonResponse({
        'paid': paid, 'status': order.payment_status, 'error': error,
        'redirect': reverse('order_complete', args=[order.order_number]) if paid else None,
    })


@csrf_exempt
def qpay_callback(request, order_number):
    """QPay төлбөр орох үед энэ хаягийг дуудна. Callback-д итгэхгүй — QPay-аас дахин шалгана."""
    order = Order.objects.filter(order_number=order_number).first()
    if order:
        _refresh_payment(order)
    return HttpResponse('SUCCESS')


@login_required
@require_POST
def qpay_cancel(request, order_number):
    """Төлөгдөөгүй захиалгыг цуцалж, үлдэгдлийг буцаана."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    paid, _ = _refresh_payment(order)          # цуцлахаас өмнө төлөгдсөн эсэхийг шалгана
    if paid:
        messages.info(request, 'Энэ захиалгын төлбөр аль хэдийн төлөгдсөн байна.')
        return redirect('order_complete', order_number=order.order_number)
    if order.payment_status != 'pending':
        return redirect('dashboard')

    with transaction.atomic():
        updated = Order.objects.filter(id=order.id, payment_status='pending').update(
            payment_status='cancelled', status='Cancelled')
        if updated:
            for item in order.items.select_related('product'):
                if item.product_id:
                    Product.objects.filter(id=item.product_id).update(
                        stock=models_F('stock') + item.quantity)
    if order.qpay_invoice_id:
        qpay.cancel_invoice(order.qpay_invoice_id)
    messages.success(request, f'#{order.order_number} захиалга цуцлагдлаа.')
    return redirect('dashboard')


@login_required
@require_POST
def qpay_simulate(request, order_number):
    """ЗӨВХӨН sandbox-д (тест товч асаалттай үед): төлбөр төлсөн мэт болгоно."""
    if not (_test_button_enabled()):
        return HttpResponse(status=404)
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    _mark_paid(order, order.grand_total)
    messages.success(request, '(Тест) Төлбөр төлөгдсөн гэж тэмдэглэлээ.')
    return redirect('order_complete', order_number=order.order_number)


@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'dashboard.html', {'orders': orders})
