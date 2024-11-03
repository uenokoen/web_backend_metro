from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.db.models import Q

from . import utils
from ..models import Route, Order, RouteOrder


def _default_context(request: HttpRequest) -> dict:
    order = utils.get_order(request)
    routes_amount = len(utils.get_routes(order))
    return {
        "order": order,
        "routes_amount": routes_amount
    }


def index(request: HttpRequest):
    return redirect("showcase-view")

def showcase(request: HttpRequest):
    query = request.GET.get('query', None)

    if query is None:
        result = Route.objects.filter(is_active=True)
    else:
        query = query.lower().strip()
        result = Route.objects.filter(
            Q(origin__icontains=query) | Q(destination__icontains=query), is_active=True
        )
    
    context = _default_context(request)
    context["data"] = result
    return render(request, "products.html", context)

def order(request: HttpRequest, id: int):
    order = Order.objects.get(id__exact=id)
    if order.status != 'DRAFT':
        return redirect("showcase-view")
    # routes = [a.route for a in RouteOrder.objects.filter(order__exact=order).select_related() if a.route.is_active] # TODO
    routes = utils.get_routes(order)
    total_cost = sum([i.price for i in routes])
    
    context = _default_context(request)
    context["data"] = routes
    context["total_cost"] = total_cost
    return render(request, "cart.html", context)

def route(request: HttpRequest, id: int):
    item = Route.objects.get(id__exact=id)

    context = _default_context(request)
    context["route"] = item
    return render(request, "product.html", context)



