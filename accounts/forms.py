from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from accounts.models import Account

class RegisterForm(ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'})
    )
    repeat_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password'})
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password')

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = "Enter Email"
        self.fields['first_name'].widget.attrs['placeholder'] = "Enter FirstName"
        self.fields['last_name'].widget.attrs['placeholder'] = "Enter LastName"
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    # Validation
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Энэ имэйл аль хэдийн бүртгэлтэй байна.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        repeat_password = cleaned_data.get("repeat_password")

        if password and repeat_password and password != repeat_password:
            raise forms.ValidationError("Нууц үгнүүд таарахгүй байна.")

        return cleaned_data


class AccountsForm(ModelForm):
    phone_number = forms.CharField(
        widget=forms.NumberInput(attrs={
            'placeholder': 'Enter phone',
            'class': 'form-control',
        })
    )

    class Meta:
        model = Account
        fields = ('phone_number', 'pro_image')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if Account.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Энэ утасны дугаар бүртгэлтэй байна.")
        return phone_number


# ---------------------------------------------------------------------------
# Профайл
# ---------------------------------------------------------------------------

class ProfileInfoForm(forms.Form):
    last_name = forms.CharField(max_length=150, label='Овог солих')
    first_name = forms.CharField(max_length=150, label='Нэр солих')
    birth_date = forms.DateField(required=False, label='Төрсөн өдөр',
                                 widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(required=False, label='Хүйс',
                               choices=[('', 'Сонгох')] + list(Account.GENDER_CHOICES))

    def clean_birth_date(self):
        import datetime
        d = self.cleaned_data.get('birth_date')
        if d and (d > datetime.date.today() or d.year < 1900):
            raise forms.ValidationError('Төрсөн өдөр буруу байна.')
        return d


class PhoneForm(forms.Form):
    phone_number = forms.CharField(max_length=20, label='Утасны дугаар')

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_phone_number(self):
        phone = ''.join(ch for ch in self.cleaned_data['phone_number'] if ch.isdigit())
        if len(phone) != 8:
            raise forms.ValidationError('8 оронтой утасны дугаар оруулна уу.')
        if Account.objects.filter(phone_number=phone).exclude(user=self.user).exists():
            raise forms.ValidationError('Энэ дугаар өөр бүртгэлд ашиглагдаж байна.')
        return phone


class AvatarForm(forms.Form):
    pro_image = forms.ImageField(label='Зураг')

    def clean_pro_image(self):
        img = self.cleaned_data['pro_image']
        if img.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Зургийн хэмжээ 5MB-аас ихгүй байх ёстой.')
        return img
