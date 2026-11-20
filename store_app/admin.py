from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, ProductSpec, ReviewRating, Wishlist


# ---------------------------------------------------------------------------
# Олон зураг нэг дор сонгох талбар
# ---------------------------------------------------------------------------

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        return [single_clean(data, initial)] if data else []


class ProductAdminForm(forms.ModelForm):
    bulk_images = MultipleImageField(
        required=False, label='Олон зураг нэг дор нэмэх',
        help_text='Ctrl (эсвэл Shift) дарж олон зураг сонгоно. Хадгалахад галерейд нэмэгдэнэ.')

    class Meta:
        model = Product
        fields = '__all__'


# ---------------------------------------------------------------------------
# Inline-ууд
# ---------------------------------------------------------------------------

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('preview', 'image', 'ordering')
    readonly_fields = ('preview',)

    @admin.display(description='Зураг')
    def preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px">', obj.image.url)
        return '—'


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 3


class ChildCategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 1
    fields = ('category_name', 'slug', 'ordering')
    prepopulated_fields = {'slug': ('category_name',)}
    verbose_name = 'Дэд ангилал'
    verbose_name_plural = 'Дэд ангиллууд'


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('__str__', 'slug', 'parent', 'ordering')
    list_filter = ('parent',)
    list_editable = ('ordering',)
    search_fields = ('category_name',)
    inlines = [ChildCategoryInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    prepopulated_fields = {'slug': ('product_name',)}
    list_display = ('thumb', 'product_name', 'brand', 'category', 'price', 'stock', 'is_available', 'views')
    list_display_links = ('thumb', 'product_name')
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('category', 'brand', 'is_available')
    search_fields = ('product_name', 'brand', 'sku')
    inlines = [ProductImageInline, ProductSpecInline]
    fieldsets = (
        (None, {'fields': ('product_name', 'slug', 'category', 'brand', 'sku')}),
        ('Үнэ, үлдэгдэл', {'fields': ('price', 'old_price', 'stock', 'is_available', 'delivery_info')}),
        ('Зураг', {'fields': ('images', 'bulk_images')}),
        ('Тайлбар', {'fields': ('description', 'additional_info')}),
    )

    @admin.display(description='')
    def thumb(self, obj):
        if obj.images:
            return format_html('<img src="{}" style="height:40px;border-radius:4px">', obj.images.url)
        return ''

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        start = form.instance.extra_images.count()
        for i, f in enumerate(form.cleaned_data.get('bulk_images') or []):
            ProductImage.objects.create(product=form.instance, image=f, ordering=start + i)


@admin.register(ReviewRating)
class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating')
    list_editable = ('status',)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('product__product_name', 'user__email')
