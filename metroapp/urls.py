from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from metroapp.controllers.views import (
    RouteListAPIView,
    RouteDetailAPIView,
    RouteImageAPIView,
    TripListAPIView,
    TripDetailAPIView,
    RouteTripAPIView,
    RouteDraftTripAPIView,
    TripModerateAPIView,
    TripFormAPIView,
    UserRegistrationAPIView, UserUpdateAPIView,
    UserAuthAPIView, UserDeauthAPIView, AttributeAPIView,
)
from metroapp.models import RouteTrip
router = routers.DefaultRouter()

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path("routes/", RouteListAPIView.as_view()),
    path("routes/<int:route_id>/", RouteDetailAPIView.as_view()),
    path("routes/<int:route_id>/image/", RouteImageAPIView.as_view()),
    path("routes/<int:route_id>/drafttrip/", RouteDraftTripAPIView.as_view()),

    path("trips/", TripListAPIView.as_view()),
    path("trips/<int:trip_id>/", TripDetailAPIView.as_view()),
    path("trips/<int:trip_id>/form/", TripFormAPIView.as_view()),
    path("trips/<int:trip_id>/finish/", TripModerateAPIView.as_view()),

    path("routes/<int:route_id>/trip/", RouteTripAPIView.as_view()),

    path("users/register/", UserRegistrationAPIView.as_view()),
    path("users/update/", UserUpdateAPIView.as_view()),
    path("users/auth/", UserAuthAPIView.as_view()),
    path("users/deauth/", UserDeauthAPIView.as_view()),

    path("routes/<int:object_id>/attributes/", AttributeAPIView.as_view()),
]
