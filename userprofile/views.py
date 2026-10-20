import hashlib
import hmac
import json
import logging
import uuid

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from home.models import Phone

from .forms import ProfileForm, SignupForm
from .models import Cart, Customer, Payment, cart_totals

logger = logging.getLogger(__name__)
PAYSTACK_URL = 'https://api.paystack.co'
MAX_QTY = 50


def _safe_url(request, url):
    return bool(url) and url_has_allowed_host_and_scheme(url, {request.get_host()}, request.is_secure())


def _customer(request):
    """The logged-in user's Customer row. Staff accounts made in the admin get one on first need."""
    customer = Customer.objects.filter(user=request.user).first()
    if customer is None:
        u = request.user
        customer = Customer.objects.create(
            user=u, username=u.username, first_name=u.first_name or u.username,
            last_name=u.last_name, email=u.email, phone='', address='')
    return customer


def _open_cart(user):
    return list(Cart.objects.filter(user=user, paid=False).select_related('phone'))


def _kobo(amount):
    return int(amount * 100)


# ---------- authentication ----------
def signout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('signin')


def signin(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', '').strip(), password=request.POST.get('password', ''))
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(next_url) if _safe_url(request, next_url) else redirect('home')
        messages.error(request, 'Username or password is incorrect.')
    return render(request, 'signin.html', {'next': next_url})


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = SignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
            messages.success(request, f'Welcome {user.username}! Your account is ready. Please log in.')
            return redirect('signin')
        for field, errors in form.errors.items():
            label = '' if field == '__all__' else f'{form.fields[field].label or field.replace("_", " ").title()}: '
            for error in errors:
                messages.error(request, f'{label}{error}')
    return render(request, 'signup.html', {'old': request.POST})


# ---------- account ----------
@login_required
def profile(request):
    return render(request, 'profile.html', {'userprof': _customer(request)})


@login_required
def profile_update(request):
    customer = _customer(request)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'profile_update.html', {'userprof': customer, 'form': form})


@login_required
def password_update(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password has been changed.')
        return redirect('profile')
    return render(request, 'password_update.html', {'userprof': _customer(request), 'form': form})


@login_required
def orders(request):
    paid = Payment.objects.filter(user=request.user, paid=True).prefetch_related('items__phone')
    return render(request, 'orders.html', {'orders': paid})


# ---------- cart ----------
@login_required
@require_POST
def add_to_cart(request):
    phone = get_object_or_404(Phone, pk=request.POST.get('phoneid'))
    if not phone.in_stock:
        messages.error(request, f'Sorry, {phone.name} is out of stock.')
        return redirect(phone.get_absolute_url())
    try:
        qty = max(1, min(MAX_QTY, int(request.POST.get('quantity', 1))))
    except ValueError:
        qty = 1

    item = Cart.objects.filter(user=request.user, phone=phone, paid=False).first()
    if item:
        item.qty = min(MAX_QTY, item.qty + qty)
        item.price = phone.final_price  # refresh to today's price
        item.save()
    else:
        Cart.objects.create(user=request.user, phone=phone, qty=qty, price=phone.final_price)

    messages.success(request, format_html('{} added to your cart. <a href="{}">View cart</a>', phone.name, reverse('cart')))
    target = request.META.get('HTTP_REFERER')
    return redirect(target) if _safe_url(request, target) else redirect('home')


@login_required
def cart(request):
    items = _open_cart(request.user)
    subtotal, vat, total = cart_totals(items)
    return render(request, 'cart.html', {'cart': items, 'subtotal': subtotal, 'vat': vat, 'total': total})


@login_required
@require_POST
def increase(request):
    item = get_object_or_404(Cart, pk=request.POST.get('quant_id'), user=request.user, paid=False)
    try:
        qty = int(request.POST.get('quant', 1))
    except ValueError:
        qty = 1
    item.qty = max(1, min(MAX_QTY, qty))
    item.save()
    messages.success(request, 'Quantity updated.')
    return redirect('cart')


@login_required
@require_POST
def delete(request):
    Cart.objects.filter(pk=request.POST.get('del_id'), user=request.user, paid=False).delete()
    messages.success(request, 'Item removed from your cart.')
    return redirect('cart')


# ---------- checkout & payment ----------
@login_required
def checkout(request):
    items = _open_cart(request.user)
    if not items:
        messages.info(request, 'Your cart is empty.')
        return redirect('cart')
    subtotal, vat, total = cart_totals(items)
    return render(request, 'checkout.html', {
        'cart': items, 'subtotal': subtotal, 'vat': vat, 'total': total, 'userprof': _customer(request)})


def _mark_paid(payment):
    """Idempotent: safe to call from both the callback and the webhook."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.paid:
            return payment
        payment.paid = True
        payment.paid_at = timezone.now()
        payment.save(update_fields=['paid', 'paid_at'])
        payment.items.update(paid=True)
    return payment


@login_required
@require_POST
def pay(request):
    items = _open_cart(request.user)
    if not items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    _, _, total = cart_totals(items)  # always recalculated here; nothing from the browser is trusted
    ref = uuid.uuid4().hex
    demo = settings.DEBUG and not settings.PAYSTACK_SECRET_KEY
    auth_url = None

    if not demo:
        try:
            response = requests.post(
                f'{PAYSTACK_URL}/transaction/initialize',
                headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
                json={'reference': ref, 'amount': _kobo(total), 'email': request.user.email, 'currency': 'NGN',
                      'callback_url': f'{settings.SITE_URL}{reverse("callback")}'},
                timeout=15)
            response.raise_for_status()
            auth_url = response.json()['data']['authorization_url']
        except (requests.RequestException, KeyError, ValueError):
            logger.exception('Paystack initialize failed')
            messages.error(request, 'The payment service is busy. Please try again in a moment.')
            return redirect('checkout')

    with transaction.atomic():
        payment = Payment.objects.create(
            user=request.user, amount=total, pay_code=ref, paid=False,
            first_name=request.POST.get('first_name', '').strip() or request.user.first_name,
            last_name=request.POST.get('last_name', '').strip() or request.user.last_name,
            phone=request.POST.get('phone', '').strip(), address=request.POST.get('address', '').strip())
        Cart.objects.filter(pk__in=[i.pk for i in items]).update(payment=payment)

    if demo:
        return redirect(f'{reverse("callback")}?reference={ref}')
    return redirect(auth_url)


@login_required
def callback(request):
    ref = request.GET.get('reference') or request.GET.get('trxref')
    payment = get_object_or_404(Payment, pay_code=ref, user=request.user)

    if not payment.paid:
        if settings.DEBUG and not settings.PAYSTACK_SECRET_KEY:
            payment = _mark_paid(payment)  # local demo checkout only
        else:
            try:
                response = requests.get(f'{PAYSTACK_URL}/transaction/verify/{ref}',
                                        headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}, timeout=15)
                data = response.json()['data']
            except (requests.RequestException, KeyError, ValueError):
                logger.exception('Paystack verify failed')
                messages.error(request, f'We could not confirm your payment yet. If you were charged, contact us with reference {ref}.')
                return redirect('orders')
            if data.get('status') != 'success' or int(data.get('amount', 0)) != _kobo(payment.amount):
                messages.error(request, 'Your payment was not successful and you have not been charged.')
                return redirect('cart')
            payment = _mark_paid(payment)

    items = list(payment.items.select_related('phone'))
    return render(request, 'callback.html', {
        'userprof': _customer(request), 'payment': payment, 'cart': items,
        'phone': items[0].phone if items else None})


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Paystack calls this even if the customer closes the tab before the callback page loads."""
    secret = settings.PAYSTACK_SECRET_KEY
    signature = request.headers.get('x-paystack-signature', '')
    expected = hmac.new(secret.encode(), request.body, hashlib.sha512).hexdigest() if secret else ''
    if not secret or not hmac.compare_digest(signature, expected):
        return HttpResponse(status=401)
    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        payment = Payment.objects.filter(pay_code=data.get('reference')).first()
        if payment and int(data.get('amount', 0)) == _kobo(payment.amount):
            _mark_paid(payment)
    return HttpResponse(status=200)
