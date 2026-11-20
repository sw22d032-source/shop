from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Category, Product, ReviewRating, Wishlist

COMPARE_LIMIT = 4

PER_PAGE = 12


def _paginate(request, products):
    return Paginator(products, PER_PAGE).get_page(request.GET.get('page'))


def _query_without_page(request):
    """Хуудаслалтын холбоос дээр хайлтын параметрүүдийг хадгалахад хэрэглэнэ."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def _open_ids(category):
    """Модонд автоматаар задрах ангиллууд: идэвхтэй ангилал ба түүний эцгүүд."""
    if not category:
        return []
    return [c.id for c in category.get_ancestors()] + [category.id]


def index(request):
    productAll = (Product.objects.filter(is_available=True)
                  .select_related('category').order_by('-created_date')[:10])
    popular = (Product.objects.filter(is_available=True)
               .select_related('category').order_by('-views', '-id')[:10])

    # Үндсэн ангилал бүрээс (дэд ангиллуудыг оруулаад) 5 бараа
    rows = []
    for cat in Category.objects.filter(parent__isnull=True):
        items = list(Product.objects.filter(
            category_id__in=cat.get_descendant_ids(), is_available=True)
            .select_related('category').order_by('-id')[:5])
        if items:
            rows.append((cat, items))

    return render(request, "index.html", {
        'productAll': productAll, 'popular': popular, 'category_rows': rows,
    })


def product_detail(request, cat_slug=None, product_slug=None):
    product = get_object_or_404(
        Product.objects.select_related('category', 'category__parent'),
        slug=product_slug, category__slug=cat_slug)

    # Үзсэн тоо (session бүрт нэг удаа)
    viewed = request.session.get('viewed_products', [])
    if product.id not in viewed:
        Product.objects.filter(id=product.id).update(views=F('views') + 1)
        request.session['viewed_products'] = (viewed + [product.id])[-200:]

    similar = (Product.objects.filter(category=product.category, is_available=True)
               .exclude(id=product.id).select_related('category')[:10])
    if len(similar) < 4 and product.category.parent_id:
        similar = (Product.objects.filter(
            category_id__in=product.category.parent.get_descendant_ids(), is_available=True)
            .exclude(id=product.id).select_related('category')[:10])
    recommended = (Product.objects.filter(is_available=True, stock__gt=0)
                   .exclude(id=product.id).exclude(id__in=[p.id for p in similar])
                   .select_related('category').order_by('-views', '?')[:10])

    reviews = product.reviews.filter(status=True).select_related('user')
    my_review = None
    if request.user.is_authenticated:
        my_review = product.reviews.filter(user=request.user).first()

    return render(request, "product-detail.html", {
        'product': product,
        'gallery': product.gallery(),
        'specs': product.specs.all(),
        'similar': similar,
        'recommended': recommended,
        'reviews': reviews,
        'review_stats': product.review_stats(),
        'my_review': my_review,
        'breadcrumb': product.category.get_ancestors() + [product.category],
    })


@login_required
@require_POST
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        rating = int(request.POST.get('rating', 5))
    except ValueError:
        rating = 5
    rating = min(max(rating, 1), 5)
    text = request.POST.get('review', '').strip()[:1000]

    _, created = ReviewRating.objects.update_or_create(
        product=product, user=request.user,
        defaults={'rating': rating, 'review': text})
    messages.success(request, 'Сэтгэгдэл нэмэгдлээ. Баярлалаа!' if created else 'Сэтгэгдэл шинэчлэгдлээ.')
    return redirect(product.get_url() + '#reviews')


def store(request, cat_slug=None):
    category = None
    products = Product.objects.filter(is_available=True)
    if cat_slug is not None:
        category = get_object_or_404(Category, slug=cat_slug)
        products = products.filter(category_id__in=category.get_descendant_ids())
    products = products.select_related('category').order_by('id')

    return render(request, "store.html", {
        'products': _paginate(request, products),
        'count': products.count(),
        'garchig': category,
        'breadcrumb': category.get_ancestors() if category else [],
        'subcategories': category.children.all() if category else [],
        'open_ids': _open_ids(category),
        'query': _query_without_page(request),
    })


def search_result(request):
    keyword = request.GET.get('keyword', '').strip()
    min_price = request.GET.get('min', '').strip()
    max_price = request.GET.get('max', '').strip()
    cat_slug = request.GET.get('category', '').strip()
    products = Product.objects.filter(is_available=True)
    category = None

    if keyword:
        products = products.filter(
            Q(product_name__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(brand__icontains=keyword) |
            Q(sku__icontains=keyword)
        )
    if cat_slug:
        category = Category.objects.filter(slug=cat_slug).first()
        if category:
            products = products.filter(category_id__in=category.get_descendant_ids())
    if min_price.isdigit():
        products = products.filter(price__gte=int(min_price))
    if max_price.isdigit():
        products = products.filter(price__lte=int(max_price))
    products = products.select_related('category').order_by('id')

    return render(request, "store.html", {
        "products": _paginate(request, products),
        "count": products.count(),
        "keyword": keyword,
        "garchig": category,
        "breadcrumb": category.get_ancestors() if category else [],
        "subcategories": category.children.all() if category else [],
        "open_ids": _open_ids(category),
        "min_price": min_price,
        "max_price": max_price,
        "query": _query_without_page(request),
    })


def lab3(request):
    products = Product.objects.all()
    return render(request, "lab3.html", {'products': products})


# ---------------------------------------------------------------------------
# Хадгалах (wishlist) ба Харьцуулах (compare)
# ---------------------------------------------------------------------------

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _back(request, fallback='index'):
    """Өмнөх хуудас руу аюулгүй буцаах."""
    url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return redirect(url)
    return redirect(fallback)


@require_POST
def wishlist_toggle(request, product_id):
    if not request.user.is_authenticated:
        login_url = reverse('accounts:signin') + '?next=' + (request.POST.get('next') or '/')
        if _is_ajax(request):
            return JsonResponse({'login_required': True, 'login_url': login_url}, status=401)
        messages.info(request, 'Бараа хадгалахын тулд нэвтэрнэ үү.')
        return redirect(login_url)

    product = get_object_or_404(Product, id=product_id)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
    count = Wishlist.objects.filter(user=request.user).count()
    msg = f'"{product.product_name}" хадгалагдлаа.' if created else f'"{product.product_name}" хадгалснаас хасагдлаа.'

    if _is_ajax(request):
        return JsonResponse({'active': created, 'count': count, 'message': msg})
    messages.success(request, msg)
    return _back(request)


@login_required
def wishlist(request):
    items = (Wishlist.objects.filter(user=request.user)
             .select_related('product', 'product__category'))
    products = [w.product for w in items]
    return render(request, 'wishlist.html', {'products': products})


@require_POST
def compare_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    ids = [i for i in request.session.get('compare', []) if isinstance(i, int)]
    if product.id in ids:
        ids.remove(product.id)
        active, msg = False, f'"{product.product_name}" харьцуулалтаас хасагдлаа.'
    else:
        ids.append(product.id)
        active, msg = True, f'"{product.product_name}" харьцуулалтад нэмэгдлээ.'
        if len(ids) > COMPARE_LIMIT:
            ids = ids[-COMPARE_LIMIT:]
            msg += f' (Дээд тал нь {COMPARE_LIMIT} бараа — хамгийн эхнийх нь хасагдлаа.)'
    request.session['compare'] = ids

    if _is_ajax(request):
        return JsonResponse({'active': active, 'count': len(ids), 'message': msg,
                             'compare_url': reverse('compare')})
    messages.success(request, msg)
    return _back(request)


@require_POST
def compare_clear(request):
    request.session['compare'] = []
    messages.success(request, 'Харьцуулалт цэвэрлэгдлээ.')
    return redirect('compare')


def compare(request):
    ids = request.session.get('compare', [])
    by_id = {p.id: p for p in Product.objects.filter(id__in=ids)
             .select_related('category').prefetch_related('specs')}
    products = [by_id[i] for i in ids if i in by_id]

    # Бүх барааны үзүүлэлтийн нэрсийг дарааллаар нь нэгтгэнэ
    spec_names = []
    for p in products:
        for s in p.specs.all():
            if s.name not in spec_names:
                spec_names.append(s.name)
    spec_rows = []
    for name in spec_names:
        values = []
        for p in products:
            v = next((s.value for s in p.specs.all() if s.name == name), '—')
            values.append(v)
        spec_rows.append({'name': name, 'values': values, 'differs': len(set(values)) > 1})

    for p in products:
        p.stats = p.review_stats()

    return render(request, 'compare.html', {
        'products': products, 'spec_rows': spec_rows, 'limit': COMPARE_LIMIT,
    })
