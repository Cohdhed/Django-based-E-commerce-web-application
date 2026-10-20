from django.urls import path

from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/password/', views.password_update, name='password_update'),
    path('orders/', views.orders, name='orders'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/', views.add_to_cart, name='addtocart'),
    path('cart/update/', views.increase, name='increase'),
    path('cart/delete/', views.delete, name='delete'),
    path('checkout/', views.checkout, name='checkout'),
    path('pay/', views.pay, name='pay'),
    path('callback/', views.callback, name='callback'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
]
