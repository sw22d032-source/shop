from django.contrib.auth.models import User
from django.db import models


class Account(models.Model):
    GENDER_CHOICES = (
        ('male', 'Эрэгтэй'),
        ('female', 'Эмэгтэй'),
        ('other', 'Бусад'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True, default='')
    pro_image = models.ImageField(upload_to='photos/accounts', blank=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name='Төрсөн өдөр')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, verbose_name='Хүйс')
    email_verified = models.BooleanField(default=False, verbose_name='Имэйл баталгаажсан')
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.user.email

    @classmethod
    def for_user(cls, user):
        """Хэрэглэгчийн Account-ыг авна, байхгүй бол (Google-ээр орсон гэх мэт) үүсгэнэ."""
        account, _ = cls.objects.get_or_create(user=user)
        return account
