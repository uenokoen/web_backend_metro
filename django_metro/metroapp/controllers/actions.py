from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect
from django.db import connection
from datetime import datetime

from . import utils
from ..models import Route, Trip, RouteTrip


def add_to_cart(request: HttpRequest):
    product_id = request.POST.get('productId', None)
    next_url = request.POST.get('next', None)
    if next_url is None:
        next_url = 'index-view'
    check = RouteTrip.objects.filter(trip=utils.get_trip(request), route=Route.objects.filter(id__exact=product_id).first()).exists()
    if not check:
        RouteTrip.objects.create(
            trip=utils.get_trip(request),
            route=Route.objects.filter(id__exact=product_id).first()
        )

    return redirect(next_url)


def form_trip(request: HttpRequest):
    fullname = request.POST.get('fullname', None)
    date_str = request.POST.get('date', None)
    if fullname is None or date_str is None:
        return HttpResponse(status=400)

    date = datetime.strptime(date_str, "%Y-%m-%d")

    trip = utils.get_trip(request)
    trip.owner = fullname
    trip.status = Trip.Status.FORMED
    trip.formed_at = date
    trip.save()

    trip_id = utils.set_new_trip(request)

    return redirect('trip-view', id=trip_id)


def delete_trip(request: HttpRequest):
    trip_id = utils.get_trip(request).id

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE trips SET status = %s WHERE id = %s;",
            [Trip.Status.DELETED, trip_id]
        )

    trip_id = utils.set_new_trip(request)
    return redirect('trip-view', id=trip_id)