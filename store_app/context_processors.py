import os

from django.conf import settings
from django.db.models import Count

from store_app.models import Category, Product, Wishlist
from carts.models import CartItem
from carts.views import get_cart


def _build_tree():
    """Бүх ангиллыг нэг query-ээр аваад мод бүтэц болгоно.

    Ангилал бүрд: .subs (дэд ангиллууд), .total (өөрийн + дэд ангиллын барааны тоо)
    """
    cats = list(Category.objects.all())
    by_parent = {}
    for c in cats:
        by_parent.setdefault(c.parent_id, []).append(c)

    own = dict(Product.objects.filter(is_available=True)
               .values_list('category_id').annotate(n=Count('id')))

    def fill(node, seen):
        node.subs = [ch for ch in by_parent.get(node.id, []) if ch.id not in seen]
        node.total = own.get(node.id, 0)
        for ch in node.subs:
            node.total += fill(ch, seen | {ch.id})
        return node.total

    top = by_parent.get(None, [])
    for c in top:
        fill(c, {c.id})
    return top, cats


def _descendants(cat):
    ids, stack = [], [cat]
    while stack:
        node = stack.pop()
        ids.append(node.id)
        stack.extend(node.subs)
    return ids


def category_data(request):
    if request.path.startswith('/admin/'):
        return {}
    top, _ = _build_tree()

    # Mega-menu: ангилал бүрийн "Хамгийн их үзсэн" 6 бараа
    for cat in top:
        cat.top_products = list(
            Product.objects.filter(category_id__in=_descendants(cat), is_available=True)
            .select_related('category').order_by('-views', '-id')[:6]
        )
    return {
        'categories': top,          # үндсэн ангиллууд (хуучин template-үүдтэй нийцтэй)
        'menu_categories': top,
        'asset_version': _asset_version(),
    }


def _asset_version():
    """theme.css өөрчлөгдөх бүрт браузер шинэ файлыг татахаар хувилбарын дугаар."""
    try:
        path = os.path.join(settings.BASE_DIR, 'static', 'css', 'theme.css')
        return int(os.path.getmtime(path))
    except OSError:
        return 1


def counter(request):
    """Header дээрх сагсны тоо. Шинэ session/сагс үүсгэхгүй."""
    cart_count = 0
    if not request.path.startswith('/admin/'):
        cart = get_cart(request)
        if cart:
            for item in CartItem.objects.filter(cart=cart, is_active=True):
                cart_count += item.quantity
    return {'cart_count': cart_count}


def user_lists(request):
    """Header-ийн тоо болон картын товчны идэвхтэй төлөвт хэрэглэнэ."""
    if request.path.startswith('/admin/'):
        return {}
    compare_ids = request.session.get('compare', [])
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user)
                            .values_list('product_id', flat=True))
    return {
        'wishlist_ids': wishlist_ids, 'wishlist_count': len(wishlist_ids),
        'compare_ids': compare_ids, 'compare_count': len(compare_ids),
    }
