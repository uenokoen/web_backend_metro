from django.http import HttpRequest
from django.db.models import Count
from ..models import Order, RouteOrder, Route


def get_order(request: HttpRequest) -> Order:
    """ Returns users current order """
    cart_order_id = request.session.get('cart_order_id', None)
    if cart_order_id is not None:
        order, _ = Order.objects.get_or_create(id=cart_order_id)
    else:
        order = Order.objects.create()
        request.session['cart_order_id'] = order.id
    return order


def set_new_order(request: HttpRequest) -> int:
    cart_order_id = Order.objects.create().id
    request.session['cart_order_id'] = cart_order_id
    return cart_order_id

def get_routes(order: Order, only_active: bool = True):
    route_ids = RouteOrder.objects.filter(order=order).values_list('route', flat=True)
    return [Route.objects.get(id=i) for i in route_ids]