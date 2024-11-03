from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect
from django.db import connection
from datetime import datetime

from . import utils
from ..models import Route, Order, RouteOrder


def add_to_cart(request: HttpRequest):
    product_id = request.POST.get('productId', None)
    next_url = request.POST.get('next', None)
    if next_url is None:
        next_url = 'index-view'

    RouteOrder.objects.create(
        order=utils.get_order(request),
        route=Route.objects.filter(id__exact=product_id).first()
    )

    return redirect(next_url)


def form_order(request: HttpRequest):
    fullname = request.POST.get('fullname', None)
    date_str = request.POST.get('date', None)
    if fullname is None or date_str is None:
        return HttpResponse(status=400)

    date = datetime.strptime(date_str, "%Y-%m-%d")

    order = utils.get_order(request)
    order.owner = fullname
    order.status = Order.Status.FORMED
    order.formed_at = date
    order.save()

    order_id = utils.set_new_order(request)

    return redirect('order-view', id=order_id)


def delete_order(request: HttpRequest):
    order_id = utils.get_order(request).id

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE orders SET status = %s WHERE id = %s;",
            [Order.Status.DELETED,order_id]
        )

    order_id = utils.set_new_order(request)
    return redirect('order-view', id=order_id)