from django.contrib import admin

from .models import Cart, Customer, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'phone')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')


class CartInline(admin.TabularInline):
    model = Cart
    extra = 0
    readonly_fields = ('phone', 'qty', 'price', 'amount')
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('pay_code', 'user', 'amount', 'paid', 'created')
    list_filter = ('paid',)
    search_fields = ('pay_code', 'user__username', 'user__email')
    readonly_fields = ('pay_code', 'amount', 'created', 'paid_at')
    inlines = [CartInline]
