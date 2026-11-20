from django.conf import settings
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse


class Category(models.Model):
    # Дэд ангилал: parent хоосон бол үндсэн ангилал
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='Эцэг ангилал')
    category_name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/categories', blank=True)
    icon = models.CharField(
        max_length=50, blank=True,
        help_text='Font Awesome icon class, жишээ нь: fa fa-mobile-alt')
    ordering = models.PositiveIntegerField(default=0, verbose_name='Эрэмбэ')

    class Meta:
        db_table = 'category_tbl'
        ordering = ['ordering', 'id']
        verbose_name = 'Ангилал'
        verbose_name_plural = 'Ангилал'

    def __str__(self):
        names = [c.category_name for c in self.get_ancestors()] + [self.category_name]
        return ' › '.join(names)

    def get_url(self):
        return reverse('products_by_category', args=[self.slug])

    def get_ancestors(self):
        """Үндсэн ангиллаас эхлэн эцэг ангиллуудын жагсаалт."""
        ancestors, node, seen = [], self.parent, set()
        while node is not None and node.id not in seen:
            seen.add(node.id)
            ancestors.insert(0, node)
            node = node.parent
        return ancestors

    def get_descendant_ids(self):
        """Өөрөө болон бүх дэд ангиллын id."""
        ids, frontier = [self.id], [self.id]
        while frontier:
            frontier = list(Category.objects.filter(parent_id__in=frontier)
                            .exclude(id__in=ids).values_list('id', flat=True))
            ids.extend(frontier)
        return ids


class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    brand = models.CharField(max_length=100, blank=True, verbose_name='Брэнд')
    sku = models.CharField(max_length=100, blank=True, verbose_name='Барааны код')
    description = models.TextField(blank=True, verbose_name='Товч тайлбар')
    additional_info = models.TextField(
        blank=True, verbose_name='Нэмэлт мэдээлэл',
        help_text='Мөр бүр шинэ мөрөөр харагдана. Гарчгийг ТОМ үсгээр бичиж болно.')
    price = models.IntegerField()
    old_price = models.IntegerField(
        null=True, blank=True, verbose_name='Хуучин үнэ',
        help_text='Хямдралтай бол хуучин үнийг оруулна')
    images = models.ImageField(upload_to='photos/products/', verbose_name='Үндсэн зураг')
    stock = models.IntegerField()
    delivery_info = models.CharField(
        max_length=100, default='24-48 цагт хүргэнэ', verbose_name='Хүргэлт')
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    views = models.PositiveIntegerField(default=0, editable=False)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "baraa_tbl"
        verbose_name = 'Бараа'
        verbose_name_plural = 'Бараа'

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return f'{self.product_name} ({self.category.category_name})'

    def gallery(self):
        """Үндсэн зураг + нэмэлт зургууд (URL-ийн жагсаалт)."""
        urls = [self.images.url] if self.images else []
        urls += [img.image.url for img in self.extra_images.all() if img.image]
        return urls

    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return round((self.old_price - self.price) * 100 / self.old_price)
        return 0

    def review_stats(self):
        stats = self.reviews.filter(status=True).aggregate(
            avg=Avg('rating'), count=Count('id'))
        stats['avg'] = round(stats['avg'] or 0, 1)
        return stats


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='photos/products/gallery/')
    ordering = models.PositiveIntegerField(default=0, verbose_name='Эрэмбэ')

    class Meta:
        ordering = ['ordering', 'id']
        verbose_name = 'Нэмэлт зураг'
        verbose_name_plural = 'Нэмэлт зургууд'

    def __str__(self):
        return f'{self.product.product_name} — зураг {self.id}'


class ProductSpec(models.Model):
    """Үзүүлэлт: Төрөл = Wifi router, Ерөнхий өнгө = Цагаан гэх мэт."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='specs')
    name = models.CharField(max_length=100, verbose_name='Нэр')
    value = models.CharField(max_length=255, verbose_name='Утга')
    ordering = models.PositiveIntegerField(default=0, verbose_name='Эрэмбэ')

    class Meta:
        ordering = ['ordering', 'id']
        verbose_name = 'Үзүүлэлт'
        verbose_name_plural = 'Үзүүлэлтүүд'

    def __str__(self):
        return f'{self.name}: {self.value}'


class ReviewRating(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    review = models.TextField(max_length=1000, blank=True)
    status = models.BooleanField(default=True, verbose_name='Харагдах')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
        verbose_name = 'Сэтгэгдэл'
        verbose_name_plural = 'Сэтгэгдлүүд'

    def __str__(self):
        return f'{self.product.product_name} — {self.rating}★'


class Wishlist(models.Model):
    """Хэрэглэгчийн хадгалсан бараа."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='wishlisted')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product')
        verbose_name = 'Хадгалсан бараа'
        verbose_name_plural = 'Хадгалсан бараа'

    def __str__(self):
        return f'{self.user} ♥ {self.product.product_name}'
