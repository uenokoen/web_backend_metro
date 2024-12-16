from django.contrib import admin
from .models import Route, Trip, RouteTrip


admin.site.register(Route)
admin.site.register(Trip)
admin.site.register(RouteTrip)
