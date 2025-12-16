from django import forms
from .models import Product,ReviewRating

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'slug', 'description', 'price', 'images', 'stock', 'is_available', 'category']
 
class ReviewForm(forms.ModelForm):
    class Meta:
        model =ReviewRating
        fields =['title','review','rating']