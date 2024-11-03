from django.urls import path
from metroapp.controllers import views, actions


urlpatterns = [
    path("", views.index, name='index-view'),
    path("showcase", views.showcase, name='showcase-view'),
    path("order/<int:id>", views.order, name='order-view'),
    path("route/<int:id>", views.route, name='route-view'),

    path("add-to-order", actions.add_to_cart, name='add-to-order-action'), 
    path("form-order", actions.form_order, name='form-order-action'),           
    path("delete-order", actions.delete_order, name='delete-order-action'),
]
