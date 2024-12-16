from django.urls import path
from metroapp.controllers.views import (
    RouteListAPIView,
    RouteDetailAPIView,
    RouteImageAPIView,
    TripListAPIView,
    TripDetailAPIView,
    RouteTripAPIView,
    TripModerateAPIView,
    TripFormAPIView,
    UserRegistrationAPIView, UserUpdateAPIView,
    UserAuthAPIView, UserDeauthAPIView,
)

urlpatterns = [
    path("routes/", RouteListAPIView.as_view()),
    path("routes/<int:route_id>/", RouteDetailAPIView.as_view()),
    path("routes/<int:route_id>/image/", RouteImageAPIView.as_view()),
    path("routes/<int:route_id>/trip/", RouteTripAPIView.as_view()),

    path("trips/", TripListAPIView.as_view()),
    path("trips/<int:trip_id>/", TripDetailAPIView.as_view()),
    path("trips/<int:trip_id>/form/", TripFormAPIView.as_view()),
    path("trips/<int:trip_id>/finish/", TripModerateAPIView.as_view()),

    path("users/register/", UserRegistrationAPIView.as_view()),
    path("users/update/", UserUpdateAPIView.as_view()),
    path("users/auth/", UserAuthAPIView.as_view()),
    path("users/deauth/", UserDeauthAPIView.as_view()),
]
