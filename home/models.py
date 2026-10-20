from decimal import Decimal

from django.db import models
from django.urls import reverse


class CompanyProfile(models.Model):
    """Site-wide settings edited in the admin. Only the first row is used."""
    name = models.CharField(max_length=50, default='DevCircle')
    logo = models.ImageField(upload_to='logo', blank=True)
    carousel1 = models.ImageField(upload_to='carousel', blank=True)
    carousel2 = models.ImageField(upload_to='carousel', blank=True)
    carousel3 = models.ImageField(upload_to='carousel', blank=True)
    favicon = models.ImageField(upload_to='favicon', blank=True)
    banner = models.ImageField(upload_to='banner', blank=True)
    about = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def carousel_images(self):
        return [img for img in (self.carousel1, self.carousel2, self.carousel3) if img]

    class Meta:
        verbose_name = 'Company profile'
        verbose_name_plural = 'Company profile'


class Type(models.Model):
    """A phone brand (Samsung, Apple...)."""
    brand = models.CharField(max_length=50)
    color = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.brand

    class Meta:
        ordering = ['brand']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'


class Phone(models.Model):
    type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name='phones')
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    pix = models.ImageField(upload_to='pix')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True)
    network = models.CharField(max_length=100, blank=True)
    launch = models.CharField(max_length=100, blank=True)
    memory = models.CharField(max_length=100, blank=True)
    camera = models.CharField(max_length=100, blank=True)
    in_stock = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    best_selling = models.BooleanField(default=False)
    latest = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('detail', args=[self.id, self.slug])

    @property
    def final_price(self):
        """What the customer pays today."""
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def on_sale(self):
        return self.final_price < self.price

    @property
    def discount_percent(self):
        if self.on_sale:
            return int(((self.price - self.final_price) / self.price * Decimal(100)).to_integral_value())
        return 0

    @property
    def specs(self):
        rows = [('Network', self.network), ('Launch', self.launch), ('Memory', self.memory), ('Camera', self.camera)]
        return [(k, v) for k, v in rows if v]

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Phone'
        verbose_name_plural = 'Phones'


class Contact(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    message = models.TextField()
    sent = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.sent:%d %b %Y})'

    class Meta:
        ordering = ['-sent']
        verbose_name = 'Contact message'
        verbose_name_plural = 'Contact messages'
