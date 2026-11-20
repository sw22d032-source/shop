import json
import secrets
import time
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.forms import AccountsForm, AvatarForm, PhoneForm, ProfileInfoForm, RegisterForm
from accounts.models import Account
from accounts.social import SocialAuthError, verify_facebook, verify_google


def _safe_next(request):
    """Нэвтэрсний дараа буцах хаяг (жишээ нь checkout)."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def _social_context():
    return {
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
        'facebook_app_id': getattr(settings, 'FACEBOOK_APP_ID', ''),
    }


def _find_user(login_input):
    """Имэйл эсвэл утасны дугаараар хэрэглэгч хайна."""
    login_input = (login_input or '').strip()
    if not login_input:
        return None
    user = User.objects.filter(email__iexact=login_input).first()
    if user:
        return user
    acc = Account.objects.filter(phone_number=login_input).select_related('user').first()
    return acc.user if acc else None


def signin(request):
    """2 алхамтай нэвтрэлт: 1) имэйл/утас  2) нууц үг."""
    if request.user.is_authenticated:
        return redirect('index')

    next_url = _safe_next(request) or ''
    ctx = {'next': next_url, 'step': 'identify', 'identifier': '', **_social_context()}

    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        ctx['identifier'] = identifier
        user_obj = _find_user(identifier)

        if password is None:
            # --- Алхам 1: имэйл / утас ---
            if not identifier:
                ctx['error'] = 'И-мэйл хаяг эсвэл утасны дугаараа оруулна уу.'
            elif user_obj is None:
                ctx['not_found'] = True
            elif not user_obj.has_usable_password():
                ctx['error'] = 'Энэ бүртгэл Google/Facebook-ээр үүссэн тул доорх товчоор нэвтэрнэ үү.'
            else:
                ctx['step'] = 'password'
                ctx['display_name'] = user_obj.first_name or user_obj.email
        else:
            # --- Алхам 2: нууц үг ---
            user = None
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Амжилттай нэвтэрлээ.')
                return redirect(next_url or 'index')
            ctx['step'] = 'password' if user_obj else 'identify'
            ctx['display_name'] = (user_obj.first_name or user_obj.email) if user_obj else ''
            ctx['error'] = 'Нууц үг буруу байна.' if user_obj else 'Бүртгэл олдсонгүй.'

    return render(request, 'accounts/signin.html', ctx)


@require_POST
def social_login(request, provider):
    """Хөтчөөс ирсэн Google/Facebook токеныг шалгаад нэвтрүүлнэ."""
    try:
        payload = json.loads(request.body or '{}')
    except ValueError:
        payload = {}
    token = payload.get('access_token', '')

    try:
        if provider == 'google':
            info = verify_google(token)
        elif provider == 'facebook':
            info = verify_facebook(token)
        else:
            return JsonResponse({'ok': False, 'error': 'Тодорхойгүй үйлчилгээ.'}, status=400)
    except SocialAuthError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    user = User.objects.filter(email__iexact=info['email']).first()
    created = False
    if user is None:
        user = User(username=uuid.uuid4().hex[:30], email=info['email'],
                    first_name=info['first_name'], last_name=info['last_name'])
        user.set_unusable_password()
        user.save()
        created = True
    elif not user.is_active:
        return JsonResponse({'ok': False, 'error': 'Энэ бүртгэл идэвхгүй байна.'}, status=403)

    # Google/Facebook имэйлийг баталгаажуулсан тул тэмдэглэнэ
    account = Account.for_user(user)
    if not account.email_verified:
        account.email_verified = True
        account.save(update_fields=['email_verified'])

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Бүртгэл үүсгэж нэвтэрлээ.' if created else 'Амжилттай нэвтэрлээ.')
    if created:
        payload['next'] = payload.get('next') or '/accounts/profile/'
    next_url = payload.get('next', '')
    if not (next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})):
        next_url = '/'
    return JsonResponse({'ok': True, 'redirect': next_url})


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

            messages.success(request, "Бүртгэл амжилттай үүслээ! Одоо нэвтэрнэ үү.")
            return redirect('accounts:signin')
    else:
        initial = {}
        prefill = request.GET.get('email', '').strip()
        if '@' in prefill:
            initial['email'] = prefill
        user_form = RegisterForm(initial=initial)
        account_form = AccountsForm(initial={'phone_number': prefill} if prefill.isdigit() else None)

    context = {
        'user_form': user_form,
        'account_form': account_form,
        **_social_context(),
    }
    return render(request, 'accounts/register.html', context)


def signout(request):
    logout(request)
    messages.success(request, "Системээс гарлаа.")
    return redirect('accounts:signin')


# ---------------------------------------------------------------------------
# Профайл / хувийн мэдээлэл
# ---------------------------------------------------------------------------

def _mask_phone(phone):
    return f'{phone[:2]}**{phone[-2:]}' if len(phone) >= 6 else phone


@login_required
def profile(request):
    account = Account.for_user(request.user)
    return render(request, 'accounts/profile.html', {
        'account': account,
        'masked_phone': _mask_phone(account.phone_number),
        'avatar_form': AvatarForm(),
    })


@login_required
def profile_info(request):
    user, account = request.user, Account.for_user(request.user)
    if request.method == 'POST':
        form = ProfileInfoForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name'].strip()
            user.last_name = form.cleaned_data['last_name'].strip()
            user.save(update_fields=['first_name', 'last_name'])
            account.birth_date = form.cleaned_data['birth_date']
            account.gender = form.cleaned_data['gender']
            account.save()
            messages.success(request, 'Хувийн мэдээлэл шинэчлэгдлээ.')
            return redirect('accounts:profile')
    else:
        form = ProfileInfoForm(initial={
            'first_name': user.first_name, 'last_name': user.last_name,
            'birth_date': account.birth_date, 'gender': account.gender,
        })
    return render(request, 'accounts/profile_info.html', {'form': form, 'account': account})


@login_required
def profile_password(request):
    user = request.user
    has_password = user.has_usable_password()
    FormClass = PasswordChangeForm if has_password else SetPasswordForm
    if request.method == 'POST':
        form = FormClass(user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)   # нэвтэрсэн хэвээр үлдэнэ
            messages.success(request, 'Нууц үг шинэчлэгдлээ.' if has_password else
                             'Нууц үг тохируулагдлаа. Одоо имэйл/утас + нууц үгээр ч нэвтэрч болно.')
            return redirect('accounts:profile')
    else:
        form = FormClass(user)
    return render(request, 'accounts/profile_password.html', {
        'form': form, 'has_password': has_password, 'account': Account.for_user(user)})


@login_required
def profile_phone(request):
    account = Account.for_user(request.user)
    if request.method == 'POST':
        form = PhoneForm(request.POST, user=request.user)
        if form.is_valid():
            account.phone_number = form.cleaned_data['phone_number']
            account.save()
            messages.success(request, 'Утасны дугаар хадгалагдлаа.')
            return redirect('accounts:profile')
    else:
        form = PhoneForm(initial={'phone_number': account.phone_number}, user=request.user)
    return render(request, 'accounts/profile_phone.html', {'form': form, 'account': account})


@login_required
@require_POST
def profile_avatar(request):
    account = Account.for_user(request.user)
    if request.POST.get('remove'):
        if account.pro_image:
            account.pro_image.delete(save=False)
        account.pro_image = ''
        account.save()
        messages.success(request, 'Профайл зураг устгагдлаа.')
        return redirect('accounts:profile')

    form = AvatarForm(request.POST, request.FILES)
    if form.is_valid():
        if account.pro_image:
            account.pro_image.delete(save=False)
        account.pro_image = form.cleaned_data['pro_image']
        account.save()
        messages.success(request, 'Профайл зураг шинэчлэгдлээ.')
    else:
        messages.error(request, ' '.join(form.errors.get('pro_image', ['Зураг буруу байна.'])))
    return redirect('accounts:profile')


EMAIL_CODE_TTL = 10 * 60        # код 10 минут хүчинтэй
EMAIL_CODE_RESEND = 60          # дахин илгээхийн өмнө 60 секунд хүлээнэ
EMAIL_CODE_MAX_TRIES = 5


@login_required
def profile_email(request):
    """Имэйл рүү 6 оронтой код илгээж баталгаажуулна."""
    user, account = request.user, Account.for_user(request.user)
    if account.email_verified:
        messages.info(request, 'Таны имэйл аль хэдийн баталгаажсан байна.')
        return redirect('accounts:profile')

    data = request.session.get('email_code') or {}
    now = time.time()
    # Өөр имэйлд зориулсан эсвэл хугацаа нь дууссан кодыг хаяна
    if data and (data.get('email') != user.email or now > data.get('expires', 0)):
        data = {}
        request.session.pop('email_code', None)

    error = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'send':
            wait = int(data.get('sent_at', 0) + EMAIL_CODE_RESEND - now)
            if wait > 0:
                error = f'{wait} секундын дараа дахин илгээнэ үү.'
            else:
                code = f'{secrets.randbelow(1000000):06d}'
                try:
                    send_mail(
                        'BlueCart — имэйл баталгаажуулах код',
                        f'Сайн байна уу,\n\nТаны баталгаажуулах код: {code}\n'
                        f'Код 10 минутын турш хүчинтэй.\n\nХэрэв та хүсэлт илгээгээгүй бол энэ имэйлийг үл тоомсорлоно уу.',
                        None, [user.email], fail_silently=False)
                except Exception:
                    error = 'Имэйл илгээж чадсангүй. Имэйлийн тохиргоог (EMAIL_HOST_USER) шалгана уу.'
                else:
                    if _email_console_mode():
                        # Хөгжүүлэлтийн горим: имэйлийн бие кодлогдож хэвлэгддэг тул кодыг тод хэвлэнэ
                        print(f'\n{"=" * 50}\n  [BlueCart] Email code for {user.email}: {code}\n{"=" * 50}\n', flush=True)
                    data = {'email': user.email, 'code': code, 'expires': now + EMAIL_CODE_TTL,
                            'sent_at': now, 'tries': 0}
                    request.session['email_code'] = data
                    messages.success(request, f'{user.email} хаяг руу код илгээлээ.')
                    return redirect('accounts:profile_email')
        elif action == 'verify':
            entered = ''.join(ch for ch in request.POST.get('code', '') if ch.isdigit())
            if not data:
                error = 'Эхлээд код илгээнэ үү.'
            elif data.get('tries', 0) >= EMAIL_CODE_MAX_TRIES:
                request.session.pop('email_code', None)
                data, error = {}, 'Хэт олон удаа буруу оруулсан. Шинэ код авна уу.'
            elif not secrets.compare_digest(entered, data['code']):
                data['tries'] = data.get('tries', 0) + 1
                request.session['email_code'] = data
                error = f'Код буруу байна. ({EMAIL_CODE_MAX_TRIES - data["tries"]} оролдлого үлдлээ)'
            else:
                account.email_verified = True
                account.save(update_fields=['email_verified', 'updated_at'])
                request.session.pop('email_code', None)
                messages.success(request, 'Имэйл амжилттай баталгаажлаа!')
                return redirect('accounts:profile')

    console_mode = _email_console_mode()
    return render(request, 'accounts/profile_email.html', {
        'account': account,
        'code_sent': bool(data),
        'error': error,
        'console_mode': console_mode,
        # Зөвхөн DEBUG + имэйл тохиргоогүй үед кодыг хуудсан дээр харуулна
        'dev_code': data.get('code') if (console_mode and settings.DEBUG) else None,
    })


def _email_console_mode():
    return settings.EMAIL_BACKEND.endswith('console.EmailBackend')
