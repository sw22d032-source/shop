from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegisterForm, AccountsForm
from django.contrib.auth.models import User
from .models import Account

def user_register(request):
    if request.method == 'POST':
        rform = RegisterForm(request.POST, request.FILES)
        aform = AccountsForm(request.POST, request.FILES)

        if rform.is_valid() and aform.is_valid():
            email = rform.cleaned_data.get('email')
            password = rform.cleaned_data.get('password')
            repeat_password = rform.cleaned_data.get('repeat_password')
            phone_number = aform.cleaned_data.get('phone_number')  # утасны дугаар

            # 1️⃣ Нууц үг хоорондоо таарч байгааг шалгах
            if password != repeat_password:
                messages.error(request, "Нууц үг хоорондоо таарахгүй байна!")
                return redirect('register')

            # 2️⃣ Email давхардаж байгаа эсэх
            if User.objects.filter(email=email).exists():
                messages.error(request, "Энэ имэйл аль хэдийн бүртгэлтэй байна!")
                return redirect('register')

             # 3️⃣ Утасны дугаар давхардаж байгаа эсэх
            if Account.objects.filter(phone_number=phone_number).exists():
                messages.error(request, "Энэ утасны дугаар аль хэдийн бүртгэлтэй байна!")
                return redirect('register')
            # User үүсгэх
            user = User(
                email=email,
                first_name=rform.cleaned_data.get('first_name'),
                last_name=rform.cleaned_data.get('last_name'),
            )

            # username автоматаар үүсгэх
            base_username = email.split('@')[0]
            username = base_username
            num = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{num}"
                num += 1
            user.username = username

            # password set
            user.set_password(password)
            user.save()

            # Account үүсгэх
            acc = aform.save(commit=False)
            acc.user = user
            if 'pro_image' in request.FILES:
                acc.pro_image = request.FILES['pro_image']
            acc.save()

            messages.success(request, "Бүртгэл амжилттай үүслээ!")
            return redirect('login')

        else:
            # Form-ийн алдааг message болгон харуулах
            for field, errors in rform.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            for field, errors in aform.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('register')

    else:
        rform = RegisterForm()
        aform = AccountsForm()
        return render(request, 'register.html', {'rform': rform, 'aform': aform})

    

@login_required(login_url='login')
def user_logout(request):
    auth.logout(request)
    return redirect('login')


def user_login(request):
    if request.method == 'POST':
        login_input = request.POST.get('email')  # email, утас, эсвэл username
        password = request.POST.get('password')

        user = None

        # 1) Email-аар хайх
        try:
            user = User.objects.get(email=login_input)
        except User.DoesNotExist:
            # 2) Утасны дугаар бол Account-аар хайх
            try:
                acc = Account.objects.get(phone_number=login_input)
                user = acc.user
            except Account.DoesNotExist:
                # 3) Username гэж үзэх
                try:
                    user = User.objects.get(username=login_input)
                except User.DoesNotExist:
                    user = None

        # Authenticate хийх
        if user:
            user = auth.authenticate(request, username=user.username, password=password)

        if user is not None:
            auth.login(request, user)
            messages.success(request, "Амжилттай нэвтэрлээ!")
            return redirect('index')
        else:
            messages.error(request, "Имэйл, утас эсвэл нууц үг буруу байна!")
            return redirect('login')

    return render(request, 'signin.html')