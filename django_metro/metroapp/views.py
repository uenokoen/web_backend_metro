from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest
from django.db.models import Q
from django.db import connection
from .models import Route, Order, OrderState


def _get_order(request: HttpRequest) -> Order:
    """ Returns user current cart """
    cart_order_id = request.session.get('cart_order_id', None)
    print(cart_order_id)
    if cart_order_id is not None:
        order, _ = Order.objects.get_or_create(id__exact=cart_order_id)
    else:
        order = Order.objects.create()
        request.session['cart_order_id'] = order.id
    return order

def index(request: HttpRequest):
    return redirect("products-page")

def products(request: HttpRequest):
    query = request.POST.get('query', None)

    if query is None:
        result = Route.objects.all()
    else:
        query = query.lower()
        result = Route.objects.filter(
            Q(origin__icontains=query) | Q(destination__icontains=query)
        )

    return render(request, "products.html", {"data": result, "order": _get_order(request)})

def add_to_cart(request: HttpRequest):
    product_id = request.POST.get('productId', None)
    next_url = request.POST.get('next', None)
    if next_url is None:
        next_url = 'index-page'

    _get_order(request).routes.add(product_id)
    return redirect(next_url)
        
def cart(request: HttpRequest, id: int):
    order = Order.objects.get(id__exact=id)
    routes = order.routes.all()
    total_cost = sum([i.price for i in routes])
    return render(request, "cart.html", 
        {
            "data": routes, 
            "total_cost": total_cost, 
            "order": order
        }
    )

def product(request: HttpRequest, id: int):
    item = Route.objects.get(id__exact=id)
    return render(request, "product.html", {
        "route": item,
        "order": _get_order(request)
    })

def pay_order(request: HttpRequest):
    order = _get_order(request)
    order.state = OrderState.objects.get(state__exact='FORMED')
    order.save()

    cart_order_id = Order.objects.create().id
    request.session['cart_order_id'] = cart_order_id

    return redirect('cart-page', id=cart_order_id)

def delete_order(request: HttpRequest):
    order_id = request.session['cart_order_id']

    with connection.cursor() as cursor:
        cursor.execute(
            (
                "UPDATE metroapp_order SET state_id = "
                "(SELECT id FROM metroapp_orderstate WHERE state = 'DELETED') "
                "WHERE id = %s;"
            ),
            [order_id]
        )

    cart_order_id = Order.objects.create().id
    request.session['cart_order_id'] = cart_order_id
    return redirect('cart-page', id=cart_order_id)