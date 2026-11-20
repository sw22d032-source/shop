from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'created_date')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'phone', 'grand_total', 'payment_status', 'status', 'created_at')
    list_filter = ('payment_status', 'status', 'created_at')
    readonly_fields = ('qpay_invoice_id', 'paid_amount', 'paid_at')
    exclude = ('qpay_qr_text', 'qpay_qr_image', 'qpay_urls')
    list_editable = ('status',)
    search_fields = ('order_number', 'first_name', 'last_name', 'phone', 'email')
    inlines = [OrderItemInline]
