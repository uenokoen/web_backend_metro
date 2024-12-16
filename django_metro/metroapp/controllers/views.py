from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from metroapp.models import Route, Trip, RouteTrip
from .serializers import RouteSerializer, TripDetailSerializer, TripSerializer, \
    UserRegistrationSerializer, UserUpdateSerializer
from .utils import get_current_user, upload_to_minio, get_trip


class RouteListAPIView(APIView):
    """
    GET: Список маршрутов
    POST: Создание маршрута
    """

    def get(self, request: Request) -> Response:
        """
        GET /api/routes/
        """
        routes = Route.objects.filter(is_active=True)
        origin = request.query_params.get('origin', None)
        destination = request.query_params.get('destination', None)
        if origin:
            routes = routes.filter(origin=origin)
        if destination:
            routes = routes.filter(destination=destination)
        serializer = RouteSerializer(routes, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        """
        POST /api/routes/
        """
        serializer = RouteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouteDetailAPIView(APIView):
    """
    GET: Получение маршрута
    PUT: Обновление маршрута
    DELETE: Деактивация маршрута
    """

    def get(self, request: Request, route_id: int) -> Response:
        """
        GET /api/routes/<id>/
        """
        route = get_object_or_404(Route, id=route_id, is_active=True)
        serializer = RouteSerializer(route)
        return Response(serializer.data)

    def put(self, request: Request, route_id: int) -> Response:
        """
        PUT /api/routes/<id>/
        """
        route = get_object_or_404(Route, id=route_id, is_active=True)
        serializer = RouteSerializer(route, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, route_id: int) -> Response:
        """
        DELETE /api/routes/<id>/
        """
        route = get_object_or_404(Route, id=route_id)
        route.is_active = False
        route.save()
        return Response({"detail": "Route marked as inactive"},
                        status=status.HTTP_204_NO_CONTENT)


class RouteImageAPIView(APIView):
    """
    POST: Загрузка изображения для маршрута
    """

    def post(self, request: Request, route_id: int) -> Response:
        """
        POST /api/routes/<id>/image/
        """
        route = get_object_or_404(Route, id=route_id)
        file = request.FILES.get("image")
        if not file:
            return Response({"error": "No file provided"},
                            status=status.HTTP_400_BAD_REQUEST)

        file_name = f"route_{route_id}.{file.name.split('.')[-1]}"
        try:
            image_url = upload_to_minio(file, file_name)
            route.thumbnail = image_url
            route.save()
            return Response({"thumbnail": route.thumbnail},
                            status=status.HTTP_200_OK)
        except RuntimeError as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TripListAPIView(APIView):
    """
    GET: Список заявок
    """

    def get(self, request: Request) -> Response:
        """
        GET /api/trips/
        """
        trips = Trip.objects.exclude(status=Trip.Status.DELETED).exclude(
            status=Trip.Status.DRAFT)
        status = request.query_params.get('status', None)
        if status:
            trips = trips.filter(status=status.upper())
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)


class TripDetailAPIView(APIView):
    """
    GET: Детали заявки
    PUT: Обновление заявки
    DELETE: Удаление заявки
    """

    def get(self, request: Request, trip_id: int) -> Response:
        """
        GET /api/trips/<id>/
        """
        trip = get_object_or_404(Trip, id=trip_id)
        serializer = TripDetailSerializer(trip)
        return Response(serializer.data)

    def put(self, request: Request, trip_id: int) -> Response:
        """
        PUT /api/trips/<id>/
        """
        trip = get_object_or_404(Trip, id=trip_id)
        serializer = TripDetailSerializer(trip, data=request.data,
                                          partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, trip_id: int) -> Response:
        """
        DELETE /api/trips/<id>/
        """
        trip = get_object_or_404(Trip, id=trip_id)
        trip.status = Trip.Status.DELETED
        trip.save()
        return Response({"detail": "Trip marked as deleted"},
                        status=status.HTTP_204_NO_CONTENT)


class RouteTripAPIView(APIView):
    """
    POST: Добавление маршрута в заявку-черновик.
    DELETE: Удаление маршрута из заявки.
    PUT: Изменение маршрута в заявке.
    """

    def post(self, request: Request, route_id: int) -> Response:
        """
        POST /api/routes/<id>/trip/
        Добавление маршрута в заявку-черновик.
        Если черновик отсутствует, он создаётся.
        """
        user = get_current_user()
        if not user:
            return Response({"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Получаем или создаём черновик для пользователя
        trip = get_trip(get_current_user())

        route = get_object_or_404(Route, id=route_id, is_active=True)

        # Проверяем, не добавлен ли уже маршрут в заявку
        if RouteTrip.objects.filter(trip=trip, route=route).exists():
            return Response({"error": "Route already added to the draft trip"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Добавляем маршрут в черновик
        RouteTrip.objects.create(trip=trip, route=route)

        return Response(
            {
                "detail": "Route added to the draft trip",
                "trip_id": trip.id,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request: Request, route_id: int) -> Response:
        """
        DELETE /api/routes/<id>/trip/
        Удаление маршрута из черновика.
        """
        user = get_current_user()
        if not user:
            return Response({"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        trip = Trip.objects.filter(user=user, status=Trip.Status.DRAFT).first()
        if not trip:
            return Response({"error": "No draft trip found"},
                            status=status.HTTP_404_NOT_FOUND)

        route = get_object_or_404(Route, id=route_id)

        # Удаляем маршрут из черновика
        route_trip = RouteTrip.objects.filter(trip=trip, route=route).first()
        if not route_trip:
            return Response({"error": "Route not found in the draft trip"},
                            status=status.HTTP_404_NOT_FOUND)

        route_trip.delete()
        return Response({"detail": "Route removed from the draft trip"},
                        status=status.HTTP_204_NO_CONTENT)

    def put(self, request: Request, route_id: int) -> Response:
        """
        PUT /api/routes/<id>/trip/
        Изменение данных маршрута в черновике (free).
        """
        user = get_current_user()

        if not user:
            return Response({"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        trip = Trip.objects.filter(user=user, status=Trip.Status.DRAFT).first()
        if not trip:
            return Response({"error": "No draft trip found"},
                            status=status.HTTP_404_NOT_FOUND)

        route = get_object_or_404(Route, id=route_id)
        route_trip = RouteTrip.objects.filter(trip=trip, route=route).first()
        if not route_trip:
            return Response({"error": "Route not found in the draft trip"},
                            status=status.HTTP_404_NOT_FOUND)

        # Изменяем данные маршрута в черновике (например, отметку о свободе)
        free = request.data.get("free")
        if free is not None:
            route_trip.free = free

        route_trip.save()
        return Response(
            {
                "detail": "Route trip updated",
                "route_id": route.id,
                "free": route_trip.free,
            },
            status=status.HTTP_200_OK,
        )


class TripFormAPIView(APIView):
    """
    PUT /trips/<id>/form/
    Формирование заявки создателем.
    """

    def post(self, request: Request, trip_id: int) -> Response:
        """
        Формирование заявки создателем.
        """
        user = get_current_user()
        if not user:
            return Response({"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, id=trip_id)

        if not trip.owner:
            return Response({"error": "Trip has no owner"},
                            status=status.HTTP_403_FORBIDDEN)

        if not trip.user or trip.user != user:
            return Response(
                {"error": "Only the owner can form the trip"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if trip.status != Trip.Status.DRAFT:
            return Response(
                {"error": "Only draft trips can be formed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not RouteTrip.objects.filter(trip=trip).exists():
            return Response({"error": "Trip must contain at least one route"},
                            status=status.HTTP_400_BAD_REQUEST)

        trip.status = Trip.Status.FORMED
        trip.formed_at = timezone.now()
        trip.save()

        serializer = TripSerializer(trip)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class TripModerateAPIView(APIView):
    def post(self, request: Request, trip_id: int) -> Response:
        """
        Завершение или отклонение заявки модератором.
        action: "finish" для завершения, "dismiss" для отклонения.
        """
        user = get_current_user()
        if not user:
            return Response({"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, id=trip_id)
        action = request.data.get('action', None)

        if trip.status != Trip.Status.FORMED:
            return Response(
                {"error": "Only formed trips can be moderated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action not in ["finish", "dismiss"]:
            return Response({"error": "Invalid action"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Завершаем или отклоняем заявку
        trip.status = Trip.Status.FINISHED if action == "finish" else Trip.Status.DISMISSED
        trip.ended_at = timezone.now()
        trip.moderator = user

        # При завершении рассчитываем общую стоимость
        if action == "finish":
            total_price = RouteTrip.objects.filter(trip=trip).aggregate(
                price_total=models.Sum("route__price")
            )["price_total"]
            trip.price_total = total_price

        trip.save()

        serializer = TripSerializer(trip)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class UserRegistrationAPIView(APIView):
    """
    POST /users/register/
    Регистрация нового пользователя.
    """

    def post(self, request: Request) -> Response:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User registered successfully"},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserUpdateAPIView(APIView):
    """
    PUT /users/update/
    Изменение данных пользователя.
    """
    def put(self, request: Request) -> Response:
        user = get_current_user()
        serializer = UserUpdateSerializer(user, data=request.data,
                                          partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User updated successfully",
                             "data": serializer.data},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAuthAPIView(APIView):
    def post(self, request: Request) -> Response:
        user = get_current_user()
        return Response(
            {"detail": f"User {user.username} authenticated successfully"},
            status=status.HTTP_200_OK)


class UserDeauthAPIView(APIView):
    def post(self, request: Request) -> Response:
        user = get_current_user()
        return Response(
            {"detail": f"User {user.username} deauthenticated successfully"},
            status=status.HTTP_200_OK)
