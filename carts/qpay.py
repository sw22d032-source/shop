"""QPay V2 API клиент (нэмэлт сан шаардахгүй, urllib ашиглана).

Баримт бичиг: https://developer.qpay.mn
  POST /v2/auth/token      — Basic Auth → access_token
  POST /v2/invoice         — нэхэмжлэх үүсгэх → invoice_id, qr_text, qr_image, urls
  POST /v2/payment/check   — төлөгдсөн эсэхийг шалгах
  DELETE /v2/invoice/{id}  — нэхэмжлэх цуцлах
"""
import base64
import json
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

TOKEN_CACHE_KEY = 'qpay_access_token'


class QPayError(Exception):
    pass


def _base_url():
    return settings.QPAY_BASE_URL.rstrip('/')


def is_sandbox():
    return 'sandbox' in _base_url()


def _request(method, path, body=None, token=None, basic=None, timeout=15):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if basic:
        raw = f'{basic[0]}:{basic[1]}'.encode()
        headers['Authorization'] = 'Basic ' + base64.b64encode(raw).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_base_url() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8') or '{}'
            return json.loads(text)
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = json.loads(e.read().decode('utf-8')).get('message', '')
        except Exception:
            pass
        if e.code == 401:
            cache.delete(TOKEN_CACHE_KEY)
        raise QPayError(f'QPay алдаа ({e.code}) {detail}'.strip())
    except (urllib.error.URLError, TimeoutError) as e:
        raise QPayError('QPay сервертэй холбогдож чадсангүй. Интернэт холболтоо шалгана уу.') from e
    except ValueError as e:
        raise QPayError('QPay-аас буруу хариу ирлээ.') from e


def get_token():
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token
    if not settings.QPAY_USERNAME or not settings.QPAY_PASSWORD:
        raise QPayError('QPay тохиргоо хийгдээгүй байна (QPAY_USERNAME / QPAY_PASSWORD).')
    data = _request('POST', '/v2/auth/token',
                    basic=(settings.QPAY_USERNAME, settings.QPAY_PASSWORD))
    token = data.get('access_token')
    if not token:
        raise QPayError('QPay токен авч чадсангүй.')
    # expires_in нь секунд эсвэл unix timestamp байж болно — аюулгүйгээр 50 мин хадгална
    expires = int(data.get('expires_in') or 3600)
    ttl = expires - int(time.time()) if expires > 10**9 else expires
    cache.set(TOKEN_CACHE_KEY, token, max(60, min(ttl - 60, 3000)))
    return token


def create_invoice(order_number, amount, description, callback_url):
    """Нэхэмжлэх үүсгэнэ → {'invoice_id', 'qr_text', 'qr_image', 'short_url', 'urls'}"""
    body = {
        'invoice_code': settings.QPAY_INVOICE_CODE,
        'sender_invoice_no': order_number,
        'invoice_receiver_code': 'terminal',
        'invoice_description': description[:255],
        'amount': int(amount),
        'callback_url': callback_url,
    }
    data = _request('POST', '/v2/invoice', body=body, token=get_token())
    if not data.get('invoice_id'):
        raise QPayError('QPay нэхэмжлэх үүсгэж чадсангүй.')
    return {
        'invoice_id': data['invoice_id'],
        'qr_text': data.get('qr_text', ''),
        'qr_image': data.get('qr_image', ''),
        'short_url': data.get('qPay_shortUrl') or data.get('qpay_shortUrl') or '',
        'urls': [
            {'name': u.get('name', ''), 'description': u.get('description', ''),
             'logo': u.get('logo', ''), 'link': u.get('link', '')}
            for u in (data.get('urls') or []) if u.get('link')
        ],
    }


def check_payment(invoice_id):
    """Төлөгдсөн дүнг буцаана (төлөгдөөгүй бол 0)."""
    body = {'object_type': 'INVOICE', 'object_id': invoice_id,
            'offset': {'page_number': 1, 'page_limit': 100}}
    data = _request('POST', '/v2/payment/check', body=body, token=get_token())
    paid = 0
    for row in data.get('rows') or []:
        if str(row.get('payment_status', '')).upper() == 'PAID':
            try:
                paid += float(row.get('payment_amount') or 0)
            except (TypeError, ValueError):
                pass
    if not paid and data.get('count') and data.get('paid_amount'):
        paid = float(data['paid_amount'])
    return paid


def cancel_invoice(invoice_id):
    try:
        _request('DELETE', f'/v2/invoice/{invoice_id}', token=get_token())
    except QPayError:
        pass  # цуцлахад алдаа гарвал захиалгыг ч гэсэн цуцална
