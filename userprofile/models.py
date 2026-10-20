from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.templatetags.static import static


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    pix = models.ImageField(upload_to='customer', blank=True)

    def __str__(self):
        return self.username or self.user.username

    @property
    def avatar_url(self):
        return self.pix.url if self.pix else static('img/avatar.png')


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_code = models.CharField(max_length=64, unique=True)
    paid = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.pay_code} ({"paid" if self.paid else "pending"})'

    class Meta:
        ordering = ['-created']


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    phone = models.ForeignKey('home.Phone', on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # unit price when it was added
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name='items')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.qty} x {self.phone.name}'

    @property
    def line_total(self):
        return self.price * self.qty

    def save(self, *args, **kwargs):
        self.amount = self.price * self.qty
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['created']


def cart_totals(items):
    """(subtotal, vat, total), rounded to kobo so it always matches what Paystack charges."""
    cent = Decimal('0.01')
    subtotal = sum((i.price * i.qty for i in items), Decimal('0')).quantize(cent)
    vat = (subtotal * Decimal(settings.VAT_RATE)).quantize(cent)
    return subtotal, vat, subtotal + vat
