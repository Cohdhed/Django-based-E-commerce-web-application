import os

from django.conf import settings
from django.db.models import Sum

from .models import CompanyProfile, Type


def _asset_version():
    """Changes whenever the stylesheet changes, so browsers never keep a stale copy."""
    try:
        return int(os.path.getmtime(settings.BASE_DIR / 'static' / 'css' / 'style.css'))
    except OSError:
        return 1


def site(request):
    """cprofile (logo, favicon, banner), dropdown (brands) and cart_count for every template."""
    count = 0
    if request.user.is_authenticated:
        from userprofile.models import Cart
        count = Cart.objects.filter(user=request.user, paid=False).aggregate(n=Sum('qty'))['n'] or 0
    return {
        'cprofile': CompanyProfile.objects.first(),
        'dropdown': Type.objects.all(),
        'cart_count': count,
        'asset_v': _asset_version(),
    }
