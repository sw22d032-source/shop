from .models import Category
def category_processor(request):
    categories = Category.objects.all()
    return {'all_categories':categories}