from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from home.models import Phone, Type
from userprofile.models import Cart, Customer, Payment

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\x9e\xb1\x00\x00\x00\x00IEND\xaeB`\x82')


def make_phone(name='Test Phone', price=1000, discount=None, **kw):
    brand, _ = Type.objects.get_or_create(brand='Brand', defaults={'slug': 'brand'})
    return Phone.objects.create(type=brand, name=name, slug=name.lower().replace(' ', '-'), price=price,
                                discount_price=discount, pix=SimpleUploadedFile('p.png', PNG, 'image/png'), **kw)


SIGNUP = {'username': 'ada', 'first_name': 'Ada', 'last_name': 'Obi', 'email': 'ada@example.com', 'phone': '08030000000',
          'address': '1 Allen Ave', 'password1': 'S3cure-pass-77', 'password2': 'S3cure-pass-77'}


class AuthTests(TestCase):
    def test_signup_creates_user_and_customer(self):
        r = self.client.post(reverse('signup'), SIGNUP)
        self.assertRedirects(r, reverse('signin'))
        self.assertEqual(Customer.objects.get(user__username='ada').phone, '08030000000')

    def test_signup_rejects_duplicate_email_and_missing_phone(self):
        self.client.post(reverse('signup'), SIGNUP)
        r = self.client.post(reverse('signup'), {**SIGNUP, 'username': 'ada2', 'phone': ''})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='ada2').exists())

    def test_login_next_is_safe(self):
        User.objects.create_user('bob', password='x-pass-12345')
        r = self.client.post(reverse('signin'), {'username': 'bob', 'password': 'x-pass-12345', 'next': 'https://evil.example/'})
        self.assertRedirects(r, reverse('home'))

    def test_protected_pages_redirect_anonymous(self):
        for name in ('cart', 'checkout', 'profile', 'orders'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)


class ShopFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'S3cure-pass-77', first_name='Ada')
        Customer.objects.create(user=self.user, username='ada', first_name='Ada', last_name='Obi',
                                email='ada@example.com', phone='080', address='Lagos')
        self.phone = make_phone(price=1000, discount=800)
        self.client.login(username='ada', password='S3cure-pass-77')

    def add(self, qty=1):
        return self.client.post(reverse('addtocart'), {'phoneid': self.phone.id, 'quantity': qty})

    def test_add_uses_discount_and_merges_rows(self):
        self.add(1); self.add(2)
        item = Cart.objects.get()
        self.assertEqual((item.qty, item.price), (3, Decimal('800.00')))

    def test_cart_totals_include_vat(self):
        self.add(2)
        r = self.client.get(reverse('cart'))
        self.assertEqual(r.context['subtotal'], Decimal('1600.00'))
        self.assertEqual(r.context['vat'], Decimal('120.00'))
        self.assertEqual(r.context['total'], Decimal('1720.00'))

    def test_cannot_touch_other_users_cart(self):
        other = User.objects.create_user('eve', password='x-pass-12345')
        theirs = Cart.objects.create(user=other, phone=self.phone, qty=1, price=800)
        self.client.post(reverse('delete'), {'del_id': theirs.id})
        r = self.client.post(reverse('increase'), {'quant_id': theirs.id, 'quant': 9})
        self.assertEqual(r.status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.qty, 1)

    def test_out_of_stock_cannot_be_added(self):
        self.phone.in_stock = False; self.phone.save()
        self.add()
        self.assertFalse(Cart.objects.exists())

    @override_settings(DEBUG=True, PAYSTACK_SECRET_KEY='')
    def test_demo_checkout_marks_paid_and_ignores_posted_total(self):
        self.add(1)
        r = self.client.post(reverse('pay'), {'first_name': 'Ada', 'last_name': 'Obi', 'phone': '080', 'address': 'Lagos', 'total': '1'})
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, Decimal('860.00'))
        self.assertFalse(payment.paid)
        self.client.get(r['Location'])
        payment.refresh_from_db()
        self.assertTrue(payment.paid)
        self.assertTrue(Cart.objects.get().paid)
        self.assertEqual(self.client.get(reverse('orders')).status_code, 200)

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_x')
    def test_paystack_flow_verifies_before_marking_paid(self):
        self.add(1)
        init = mock.Mock(); init.json.return_value = {'data': {'authorization_url': 'https://paystack.test/pay'}}
        with mock.patch('userprofile.views.requests.post', return_value=init) as post:
            r = self.client.post(reverse('pay'), {'total': '1'})
        self.assertEqual(r['Location'], 'https://paystack.test/pay')
        self.assertEqual(post.call_args.kwargs['json']['amount'], 86000)
        payment = Payment.objects.get()
        self.assertFalse(payment.paid)

        failed = mock.Mock(); failed.json.return_value = {'data': {'status': 'abandoned', 'amount': 86000}}
        with mock.patch('userprofile.views.requests.get', return_value=failed):
            self.client.get(reverse('callback'), {'reference': payment.pay_code})
        payment.refresh_from_db(); self.assertFalse(payment.paid)

        wrong_amount = mock.Mock(); wrong_amount.json.return_value = {'data': {'status': 'success', 'amount': 100}}
        with mock.patch('userprofile.views.requests.get', return_value=wrong_amount):
            self.client.get(reverse('callback'), {'reference': payment.pay_code})
        payment.refresh_from_db(); self.assertFalse(payment.paid)

        ok = mock.Mock(); ok.json.return_value = {'data': {'status': 'success', 'amount': 86000}}
        with mock.patch('userprofile.views.requests.get', return_value=ok):
            self.client.get(reverse('callback'), {'reference': payment.pay_code})
        payment.refresh_from_db(); self.assertTrue(payment.paid)

    @override_settings(DEBUG=False, PAYSTACK_SECRET_KEY='')
    def test_no_demo_checkout_in_production(self):
        self.add(1)
        with mock.patch('userprofile.views.requests.post', side_effect=__import__('requests').ConnectionError):
            r = self.client.post(reverse('pay'), {})
        self.assertRedirects(r, reverse('checkout'), fetch_redirect_response=False)
        self.assertFalse(Payment.objects.exists())

    def test_callback_without_valid_reference_is_404(self):
        self.assertEqual(self.client.get(reverse('callback')).status_code, 404)
        self.assertEqual(self.client.get(reverse('callback'), {'reference': 'nope'}).status_code, 404)

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_x')
    def test_webhook_requires_valid_signature(self):
        import hashlib, hmac, json
        payment = Payment.objects.create(user=self.user, amount=Decimal('860.00'), pay_code='ref123')
        body = json.dumps({'event': 'charge.success', 'data': {'reference': 'ref123', 'amount': 86000}}).encode()
        bad = self.client.post(reverse('paystack_webhook'), body, content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE='bad')
        self.assertEqual(bad.status_code, 401)
        sig = hmac.new(b'sk_test_x', body, hashlib.sha512).hexdigest()
        good = self.client.post(reverse('paystack_webhook'), body, content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE=sig)
        self.assertEqual(good.status_code, 200)
        payment.refresh_from_db(); self.assertTrue(payment.paid)

    def test_profile_update_syncs_user(self):
        r = self.client.post(reverse('profile_update'), {'first_name': 'Adaeze', 'last_name': 'Obi', 'email': 'new@example.com', 'phone': '081', 'address': 'Abuja'})
        self.assertRedirects(r, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email), ('Adaeze', 'new@example.com'))

    def test_all_pages_render(self):
        for name in ('home', 'products', 'about', 'contact', 'cart', 'profile', 'profile_update', 'password_update', 'orders'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(self.phone.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(reverse('category', args=[self.phone.type.id, 'brand'])).status_code, 200)
        self.add()
        self.assertEqual(self.client.get(reverse('checkout')).status_code, 200)
