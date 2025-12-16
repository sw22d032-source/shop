from django.contrib import admin
from .models import *

class ProductImageLine(admin.TabularInline):
    model = ImageGallery
    extra = 2
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('category_name',)}
admin.site.register(Category, CategoryAdmin)


class ProductImageLine(admin.TabularInline):
    model = ImageGallery
    extra = 2
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('product_name',)}
    inlines =[
        ProductImageLine
    ]
admin.site.register(Product, ProductAdmin)