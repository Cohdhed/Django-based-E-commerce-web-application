"""python manage.py seed_demo [--reset]

Fills the shop with a sample catalogue built from the photos in seed_assets/.
Names and prices are SAMPLES: edit them (or delete them) in /admin/.
"""
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from home.models import CompanyProfile, Phone, Type

ASSETS = Path(settings.BASE_DIR) / 'seed_assets'

# (brand, name, image, price, discount, featured, best_selling, latest, description)
PHONES = [
    ('Apple', 'iPhone 13 Pro (Sierra Blue)', 'iphone-13-pro-blue', 980000, 940000, True, False, False, 'Pro camera system and a bright 6.1-inch display.'),
    ('Apple', 'iPhone 13 Pro (Gold)', 'iphone-13-pro-gold', 990000, None, True, False, True, 'Pro camera system and a bright 6.1-inch display.'),
    ('Apple', 'iPhone X (Renewed)', 'iphone-x-renewed', 285000, None, False, True, False, 'Renewed and checked, no scratches.'),
    ('Apple', 'iPhone 7 Plus (PRODUCT)RED', 'iphone-7-plus-red', 230000, 215000, False, True, False, 'Dual-camera iPhone in the special red finish.'),
    ('Samsung', 'Galaxy S21+', 'galaxy-s21', 520000, None, True, False, True, 'Phantom Violet with a triple rear camera.'),
    ('Samsung', 'Galaxy Note 9', 'galaxy-note-9', 330000, 295000, False, True, False, 'Big AMOLED screen with the S Pen included.'),
    ('Infinix', 'Infinix Hot 11 Play', 'infinix-a', 105000, None, False, False, False, 'Everyday phone with a big battery.'),
    ('Infinix', 'Infinix Hot 11S', 'infinix-b', 125000, 115000, False, True, False, 'FHD+ display and a 5200mAh battery.'),
    ('Infinix', 'Infinix Note 11 Pro', 'infinix-c', 240000, None, True, False, True, 'Colour-shifting back and a square camera module.'),
    ('Infinix', 'Infinix Note 11', 'infinix-d', 215000, None, False, False, True, 'Slim metallic finish with a triple camera.'),
]


def asset(name):
    return ContentFile((ASSETS / name).read_bytes())


class Command(BaseCommand):
    help = 'Create sample brands, phones and company profile from seed_assets/'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='delete all existing phones and brands first')

    def handle(self, *args, **options):
        if options['reset']:
            Phone.objects.all().delete()
            Type.objects.all().delete()

        profile, _ = CompanyProfile.objects.get_or_create(pk=1, defaults={
            'name': 'DevCircle',
            'about': 'Team DevCircle sells genuine phones at clear prices and delivers them to your door.'})
        if not profile.logo:
            profile.logo.save('logo.png', asset('logo.png'), save=False)
        if not profile.favicon:
            profile.favicon.save('favicon.png', asset('favicon.png'), save=False)
        if not profile.carousel1:
            profile.carousel1.save('promo-samsung.jpg', asset('promo-samsung.jpg'), save=False)
        if not profile.carousel2:
            profile.carousel2.save('promo-huawei.jpg', asset('promo-huawei.jpg'), save=False)
        profile.save()

        brands = {}
        for brand, *_ in PHONES:
            brands[brand] = Type.objects.get_or_create(brand=brand, defaults={'slug': slugify(brand)})[0]

        for brand, name, image, price, discount, featured, best, latest, desc in PHONES:
            phone, created = Phone.objects.get_or_create(slug=slugify(name), defaults=dict(
                type=brands[brand], name=name, price=price, discount_price=discount, description=desc,
                featured=featured, best_selling=best, latest=latest, pix='pix/pending.jpg'))
            if created:
                phone.pix.save(f'{image}.jpg', asset(f'{image}.jpg'), save=True)
        self.stdout.write(self.style.SUCCESS(
            f'{Phone.objects.count()} phones, {Type.objects.count()} brands ready. Sample prices: edit them in /admin/.'))
