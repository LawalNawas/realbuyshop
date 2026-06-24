from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),

    path('register/', views.register_view, name='register'),

    path('search/', views.product_search, name='product_search'),

    path('search/', views.search_results, name='search_results'),

    path('profile/', views.profile_view, name='profile'),

    path('products/', views.product_list, name='products'),

    path('cart/', views.cart_view, name='cart'),

    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    path('payment/initiate/<int:order_id>/', views.initiate_payment, name='initiate_payment'),
    
    path('payment/verify/<int:order_id>/', views.verify_payment, name='verify_payment'),
    

    path(
        'products/<slug:slug>/',
        views.product_detail,
        name='product_detail'
    ),

    

    path(
        'remove-from-cart/<int:item_id>/',
        views.remove_from_cart,
        name='remove_from_cart'
    ),

    path(
        'checkout/',
        views.checkout,
        name='checkout'
    ),

    path(
        'order-success/<int:order_id>/',
        views.order_success,
        name='order_success'
    ),

    path(
        'orders/',
        views.orders_view,
        name='orders'
    ),

    path(
        'orders/<int:order_id>/',
        views.order_detail,
        name='order_detail'
    ),

    
]