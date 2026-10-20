from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ContactForm
from .models import CompanyProfile, Phone, Type

PRODUCT_SORTS = {
    'newest': ('Newest', '-uploaded_at'),
    'price_asc': ('Price: low to high', 'price'),
    'price_desc': ('Price: high to low', '-price'),
    'name': ('Name', 'name'),
}
PAGE_SIZE = 8


def _listing(request, queryset):
    """Search (?q=), sort (?sort=) and paginate a Phone queryset."""
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(type__brand__icontains=q))
    sort = request.GET.get('sort', 'newest')
    if sort not in PRODUCT_SORTS:
        sort = 'newest'
    queryset = queryset.order_by(PRODUCT_SORTS[sort][1], 'id')
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return {
        'pagin': page, 'q': q, 'sort': sort,
        'sorts': [(key, label) for key, (label, _) in PRODUCT_SORTS.items()],
        'query_string': params.urlencode(),
    }


def home(request):
    base = Phone.objects.select_related('type')
    return render(request, 'index.html', {
        'featured': base.filter(featured=True)[:8],
        'bestselling': base.filter(best_selling=True)[:8],
        'latest': base.filter(latest=True)[:8],
    })


def products(request):
    return render(request, 'product.html', _listing(request, Phone.objects.select_related('type')))


def category(request, id, slug):
    categ = get_object_or_404(Type, pk=id)
    context = _listing(request, Phone.objects.select_related('type').filter(type=categ))
    context['categ'] = categ
    return render(request, 'category.html', context)


def detail(request, id, slug):
    phonedet = get_object_or_404(Phone.objects.select_related('type'), pk=id)
    related = Phone.objects.select_related('type').filter(type=phonedet.type).exclude(pk=phonedet.pk)[:4]
    return render(request, 'detail.html', {'phonedet': phonedet, 'related': related})


def about(request):
    return render(request, 'about.html', {'abouttab': CompanyProfile.objects.first()})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Thanks! Your message has been sent and we will reply shortly.')
        return redirect('home')
    return render(request, 'contact.html', {'contact': form})


def not_found(request, exception):
    return render(request, '404.html', status=404)
