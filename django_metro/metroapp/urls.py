from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name='index-page'),
    path("products", views.products, name='products-page'),
    path("cart/<int:id>", views.cart, name='cart-page'),
    path("product/<int:id>", views.product, name='product-page'),
    path("add-to-cart", views.add_to_cart, name='add-to-cart'),
    path("pay-order", views.pay_order, name='pay-order'),
    path("delete-order", views.delete_order, name='delete-order'),
]