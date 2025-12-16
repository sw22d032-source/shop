from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.forms import RegisterForm, AccountsForm
from accounts.models import Account
import uuid

def signin(request):
    if request.method == 'POST':
        login_input = request.POST.get('email')
        password = request.POST.get('password')

        user = None

        # === 1) Email-ээр login ===
        try:
            user_obj = User.objects.get(email=login_input)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

        # === 2) Phone-оор login ===
        if user is None:
            try:
                acc = Account.objects.get(phone_number=login_input)
                user = authenticate(username=acc.user.username, password=password)
            except Account.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            return redirect('store')
        else:
            messages.error(request, "Invalid email / phone or password")

    return render(request, 'accounts/signin.html')


def register(request):
    if request.method == 'POST':
        user_form = RegisterForm(request.POST)
        account_form = AccountsForm(request.POST, request.FILES)

        if user_form.is_valid() and account_form.is_valid():
            user = user_form.save(commit=False)
            user.username = uuid.uuid4().hex[:30]  # random username
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            account = account_form.save(commit=False)
            account.user = user
            account.save()

            messages.success(request, "Account created successfully!")
            return redirect('accounts:signin')
        else:
            # Form errors-г message-ээр дамжуулах
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            for field, errors in account_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('accounts:register')
    else:
        user_form = RegisterForm()
        account_form = AccountsForm()

    context = {
        'user_form': user_form,
        'account_form': account_form
    }
    return render(request, 'accounts/register.html', context)


def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('accounts:signin')
