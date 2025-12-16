from django.shortcuts import render, redirect, get_object_or_404
from shop_app.models import Product
from .models import Cart, CartItem

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.stock < 1:
        return redirect('cart')  # эсвэл тухайн бүтээгдэхүүний дэлгэрэнгүй хуудас руу буцаах

    # Сагсыг авах эсвэл үүсгэх
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # Сагсны зүйлд нэмэх
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        if cart_item.quantity < product.stock:  # Дээд хязгаар
            cart_item.quantity += 1
            cart_item.save()
            
    except CartItem.DoesNotExist:
        CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )

    return redirect('cart')


def remove_cart(request, product_id):
    """Сагснаас тухайн бүтээгдэхүүний тоог 1-ээр хасна."""
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(product=product, cart=cart)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')


def remove_cart_item(request, product_id):
    """Бүтээгдэхүүнийг сагснаас бүрэн устгана."""
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(product=product, cart=cart)
    cart_item.delete()
    return redirect('cart')


def cart(request,total = 0,quantity = 0,cart_items =None):
    """Сагсны хуудас"""
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
    tax=(2 * total)/100
    grand = total + tax
    context = {
        'tax':tax,
        'grand':grand,
        'cart_items': cart_items,
        'total': total,
        'quantity': quantity,
    }
    return render(request, 'cart.html', context)
