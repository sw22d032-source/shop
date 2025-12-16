from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
class Category(models.Model):
    category_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    cat_image = models.ImageField(upload_to='photos/categories', blank=True, null=True)

    class Meta:
        db_table = 'tbl_category'

    def __str__(self):
        return self.category_name
    
    def get_url(self):
        return reverse('store', args=[self.slug])
class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=500, blank=True)
    price = models.IntegerField()
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'tbl_product'
    def __str__ (self):
        return self.product_name
    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])
    
class ImageGallery(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='shop/products',max_length=255)
    
    def __str__ (self):
        return self.product.product_name
    
class ReviewRating(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    review = models.TextField(max_length=500)
    rating = models.FloatField()
    created_date = models.DateField(auto_now_add=True)
    ip = models.CharField(max_length=100)

    def __str__(self):
        return self.title

    @property
    def likes(self):
        return self.reactions.filter(reaction=1).count()
    @property
    def dislikes(self):
        return self.reactions.filter(reaction=-1).count()

    
class ReviewReaction(models.Model):
    review = models.ForeignKey(ReviewRating, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.IntegerField(choices=[(1, "Like"), (-1, "Dislike")])
class Meta:
    unique_together = ('review', 'user')

