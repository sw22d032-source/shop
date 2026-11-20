from django.conf import settings
from django.db import models
from store_app.models import Product

# НӨАТ (татвар) — 10%
TAX_RATE = 0.10


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f'{self.product.product_name} x {self.quantity}'


class Order(models.Model):
    STATUS_CHOICES = (
        ('New', 'Шинэ'),
        ('Accepted', 'Хүлээн авсан'),
        ('Completed', 'Хүргэгдсэн'),
        ('Cancelled', 'Цуцлагдсан'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100)
    city = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    note = models.CharField(max_length=255, blank=True)
    order_total = models.IntegerField()
    tax = models.IntegerField()
    grand_total = models.IntegerField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='New')
    created_at = models.DateTimeField(auto_now_add=True)

    # ---- Төлбөр (QPay) ----
    PAYMENT_CHOICES = (
        ('pending', 'Төлбөр хүлээгдэж буй'),
        ('paid', 'Төлөгдсөн'),
        ('cancelled', 'Цуцлагдсан'),
    )
    payment_method = models.CharField(max_length=20, default='qpay')
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default='pending')
    paid_amount = models.IntegerField(default=0)
    paid_at = models.DateTimeField(null=True, blank=True)
    qpay_invoice_id = models.CharField(max_length=100, blank=True)
    qpay_qr_text = models.TextField(blank=True)
    qpay_qr_image = models.TextField(blank=True)
    qpay_short_url = models.CharField(max_length=255, blank=True)
    qpay_urls = models.JSONField(default=list, blank=True)

    @property
    def is_paid(self):
        return self.payment_status == 'paid'

    class Meta:
        ordering = ['-created_at']

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    price = models.IntegerField()
    quantity = models.IntegerField()

    def sub_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'
