from django.contrib import admin
from .models import *


admin.site.register(Route)
admin.site.register(Trip)
admin.site.register(RouteTrip)
admin.site.register(Attribute)
admin.site.register(RouteAttributeValue)
