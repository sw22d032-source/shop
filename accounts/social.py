"""Google / Facebook нэвтрэлтийн токеныг сервер талд шалгах.

Нэмэлт сан суулгах шаардлагагүй (urllib ашиглана).
Хөтөч талд ирсэн токеныг ШУУД итгэхгүй — Google/Facebook-оос өөрсдөөс нь
токен үнэн эсэх, манай апп-д зориулж гаргасан эсэхийг асууж баталгаажуулна.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


class SocialAuthError(Exception):
    pass


def _get_json(url, headers=None, timeout=8):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise SocialAuthError(f'Токен хүчингүй байна ({e.code}).')
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise SocialAuthError('Нэвтрэлтийн сервертэй холбогдож чадсангүй. Интернэтээ шалгана уу.')


def verify_google(access_token):
    """Google OAuth access token → {'email', 'first_name', 'last_name'}"""
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if not client_id:
        raise SocialAuthError('Google нэвтрэлт тохируулагдаагүй байна (GOOGLE_CLIENT_ID).')
    if not access_token:
        raise SocialAuthError('Токен ирсэнгүй.')

    # 1) Токен манай апп-д зориулж гаргагдсан эсэх
    info = _get_json('https://oauth2.googleapis.com/tokeninfo?' +
                     urllib.parse.urlencode({'access_token': access_token}))
    if info.get('aud') != client_id and info.get('azp') != client_id:
        raise SocialAuthError('Энэ токен манай сайтад зориулагдаагүй байна.')

    # 2) Хэрэглэгчийн мэдээлэл
    user = _get_json('https://openidconnect.googleapis.com/v1/userinfo',
                     headers={'Authorization': f'Bearer {access_token}'})
    email = (user.get('email') or '').strip().lower()
    if not email or not user.get('email_verified', False):
        raise SocialAuthError('Google бүртгэлийн имэйл баталгаажаагүй байна.')
    return {
        'email': email,
        'first_name': user.get('given_name', '')[:150],
        'last_name': user.get('family_name', '')[:150],
    }


def verify_facebook(access_token):
    """Facebook access token → {'email', 'first_name', 'last_name'}"""
    app_id = getattr(settings, 'FACEBOOK_APP_ID', '')
    app_secret = getattr(settings, 'FACEBOOK_APP_SECRET', '')
    if not app_id or not app_secret:
        raise SocialAuthError('Facebook нэвтрэлт тохируулагдаагүй байна (FACEBOOK_APP_ID / SECRET).')
    if not access_token:
        raise SocialAuthError('Токен ирсэнгүй.')

    # 1) Токен манай апп-ийнх, хүчинтэй эсэх
    debug = _get_json('https://graph.facebook.com/debug_token?' + urllib.parse.urlencode({
        'input_token': access_token, 'access_token': f'{app_id}|{app_secret}'}))
    data = debug.get('data', {})
    if not data.get('is_valid') or str(data.get('app_id')) != str(app_id):
        raise SocialAuthError('Facebook токен хүчингүй байна.')

    # 2) Хэрэглэгчийн мэдээлэл
    me = _get_json('https://graph.facebook.com/me?' + urllib.parse.urlencode({
        'fields': 'id,email,first_name,last_name', 'access_token': access_token}))
    email = (me.get('email') or '').strip().lower()
    if not email:
        raise SocialAuthError('Facebook бүртгэлд имэйл байхгүй тул нэвтрэх боломжгүй. Имэйлээр бүртгүүлнэ үү.')
    return {
        'email': email,
        'first_name': me.get('first_name', '')[:150],
        'last_name': me.get('last_name', '')[:150],
    }
