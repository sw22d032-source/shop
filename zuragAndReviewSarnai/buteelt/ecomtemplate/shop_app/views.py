from django.shortcuts import render, get_object_or_404,redirect
from .models import Product, Category
from django.core.paginator import Paginator
from . import forms
from django.db.models import Q,Avg
from .models import *
from django.contrib import messages
from shop_app.forms import ReviewForm

def index(request):
    # All categories
    categories = Category.objects.all()
    # Latest 8 products
    latest_products = Product.objects.order_by('-id')[:8]
    for product in latest_products:
        product.average_rating = ReviewRating.objects.filter(
            product=product
        ).aggregate(Avg('rating'))['rating__avg'] or 0
    context = {
        'categories': categories,
        'latest_products': latest_products,
    }
    return render(request, 'index.html', context)
def itemAdd(request):
    # forms.py дотор ItemForm эсвэл ProductForm гэж нэртэй form байгаа бол
    itemForm = forms.ProductForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and itemForm.is_valid():
        itemForm.save()
        return redirect('index')

    return render(request, 'add/product_add.html', {'itemForm': itemForm})


def dashboard(request):
    return render(request, "dashboard.html")


def order_complete(request):
    return render(request, "order_complete.html")


def product_detail(request, category_slug, product_slug):
    # Get main product
    product = get_object_or_404(Product, category__slug=category_slug, slug=product_slug)

    # Stock check
    stock = product.stock > 0

    # Product gallery
    product_images = ImageGallery.objects.filter(product_id=product.id)

    # Product rating AVG
    reviews = ReviewRating.objects.filter(product=product).select_related("user", "user__account").order_by("-created_date")
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    can_review = False

    if request.user.is_authenticated:
        exists = ReviewRating.objects.filter(user=request.user, product=product).exists()
        if not exists:
            can_review = True

    

    context = {
        'single_product': product,
        'stock': stock,
        'product_images': product_images,
        'reviews': reviews,
        'average_rating': round(average_rating, 1),
        'can_review': can_review,

    }

    return render(request, 'product_detail.html', context)



def register(request):
    return render(request, "register.html")


def search_result(request):
    return render(request, "search_result.html")


def signin(request):
    return render(request, "signin.html")


def store(request, category_slug=None):
    # All categories
    categories = Category.objects.all()

    # Filter products by category slug if provided
    products = Product.objects.all()
    if category_slug:
        products = products.filter(category__slug=category_slug)

    for product in products:
        product.average_rating = ReviewRating.objects.filter(
            product=product
        ).aggregate(Avg('rating'))['rating__avg'] or 0

    # Pagination (1 page-д 2 product)
    paginator = Paginator(products, 3)
    page_number = request.GET.get('page', 1)
    paged_products = paginator.get_page(page_number)

    context = {
        "categories": categories,
        "products": paged_products,  # Page object (paged products)
        "is_paginated": paged_products.has_other_pages(),  # Хуудаслах хэрэгтэй эсэх
        "previous_page": paged_products.has_previous(),
        "next_page": paged_products.has_next(),
        "page_range": paginator.page_range,
        "total": products.count(),
    }

    return render(request, "store.html", context)

def search(request):
    keyword = request.GET.get('keyword')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    category_id = request.GET.get('category')

    # "None" string-ийг устгах
    if not keyword or keyword == "None":
        keyword = None

    products = Product.objects.all()

    # Category шүүлт
    if category_id and category_id.isdigit():
        products = products.filter(category__id=int(category_id))

    # Keyword шүүлт
    if keyword:
        products = products.filter(
            Q(product_name__icontains=keyword) |
            Q(description__icontains=keyword)
        )

    # Үнэ шүүлт
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    products = products.order_by('price')

    categories = Category.objects.all()
    total = products.count()

    context = {
        'products': products,
        'total': total,
        'keyword': keyword,
        'min_price': min_price,
        'max_price': max_price,
        'category_id': category_id,
        'categories': categories,
    }
    return render(request, "store.html", context)

def place_order(request):
    return render(request, "place_order.html")

def submit_review(request, product_id):
    product = get_object_or_404(Product,id=product_id)
    url =request.META.get('HTTP_REFERER')
    review_qs =ReviewRating.objects.filter(user=request.user,product=product)
    if review_qs.exists():
        review =review_qs.first()
    else:
        review=ReviewRating(user=request.user,product=product)
    form = ReviewForm(request.POST,instance=review)
    if form.is_valid():
        form.save()
        messages.success(request,"Таны review амжилттай илгээгдлээ")
    else:
         messages.error(request,"Алдаа : Таны review  эсвэл  rating талбар дутуу байна")
    return redirect(url)

def review_react(request, review_id, action):
    if not request.user.is_authenticated:
        return redirect('login')

    review = get_object_or_404(ReviewRating, id=review_id)

    # Like = 1, Dislike = -1
    reaction_value = 1 if action == "like" else -1

    existing = ReviewReaction.objects.filter(
        review=review,
        user=request.user
    ).first()

    if existing:
        # Хэрвээ ижил реакц дарвал устгана (toggle)
        if existing.reaction == reaction_value:
            existing.delete()
        else:
            existing.reaction = reaction_value
            existing.save()
    else:
        ReviewReaction.objects.create(
            review=review,
            user=request.user,
            reaction=reaction_value
        )

    return redirect(request.META.get('HTTP_REFERER', '/'))