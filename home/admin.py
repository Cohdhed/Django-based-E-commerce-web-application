from django.contrib import admin

from .models import CompanyProfile, Contact, Phone, Type


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Type)
class TypeAdmin(admin.ModelAdmin):
    list_display = ('brand', 'slug')
    prepopulated_fields = {'slug': ('brand',)}
    search_fields = ('brand',)


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'price', 'discount_price', 'in_stock', 'featured', 'best_selling', 'latest')
    list_filter = ('type', 'in_stock', 'featured', 'best_selling', 'latest')
    list_editable = ('in_stock', 'featured', 'best_selling', 'latest')
    search_fields = ('name', 'type__brand')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'sent', 'handled')
    list_filter = ('handled',)
    list_editable = ('handled',)
    readonly_fields = ('sent',)
