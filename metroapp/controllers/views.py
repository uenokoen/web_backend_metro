import uuid

import redis
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.db import models
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import lower
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from metroapp.models import Route, Trip, RouteTrip, Attribute, RouteAttributeValue
from .permissions import is_moderator, is_authenticated, is_admin, is_guest
from .serializers import RouteSerializer, TripDetailSerializer, TripSerializer, \
    UserRegistrationSerializer, UserUpdateSerializer, DraftTripSerializer, UserAuthSerializer, RoutePicSerializer
from .utils import get_current_user, upload_to_minio, get_trip
from .singletons import CreatorSingleton
from ..services.qr_generate import generate_trip_qr

session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator

class RouteListAPIView(APIView):
    """
    GET: Список маршрутов
    POST: Создание маршрута
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='get')
    def get(self, request: Request) -> Response:
        """
        GET /api/routes/
        """
        origin = request.query_params.get('origin', None)
        destination = request.query_params.get('destination', None)

        # Фильтрация маршрутов
        routes = Route.objects.filter(is_active=True)
        if origin:
            routes = routes.filter(origin__icontains=origin)
        if destination:
            routes = routes.filter(destination__icontains=destination)

        route_data = RouteSerializer(routes, many=True).data
        draft_trip_data = None

        if request.user.is_authenticated:
            draft_trip = Trip.objects.filter(status="DRAFT", user=request.user).first()
            draft_trip_data = DraftTripSerializer(draft_trip).data if draft_trip else None

        return Response({
            'routes': route_data,
            'draft_trip': draft_trip_data,
        })

    @swagger_auto_schema(method='post')
    @method_permission_classes((is_moderator,))
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
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='get')
    def get(self, request: Request, route_id: int) -> Response:
        """
        GET /api/routes/<id>/
        """
        route = get_object_or_404(Route, id=route_id, is_active=True)
        serializer = RouteSerializer(route)
        return Response(serializer.data)

    @swagger_auto_schema(method='put')
    @method_permission_classes((is_moderator,))
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

    @swagger_auto_schema(method='delete')
    @method_permission_classes((is_moderator,))
    def delete(self, request: Request, route_id: int) -> Response:
        """
        DELETE /api/routes/<id>/
        """
        route = get_object_or_404(Route, id=route_id)
        route.is_active = False
        route.thumbnail = ""
        route.save()
        return Response({"detail": "Route marked as inactive"},
                        status=status.HTTP_204_NO_CONTENT)


class RouteImageAPIView(APIView):
    """
    POST: Загрузка изображения для маршрута
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(request_body=RoutePicSerializer, operation_summary="add pic")
    @method_permission_classes((is_moderator,))
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
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='get')
    @method_permission_classes((is_authenticated,))
    def get(self, request: Request) -> Response:
        """
        GET /api/trips/
        """
        # Убедимся, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)

        # Базовый фильтр: исключение удалённых и черновых статусов
        trips = Trip.objects.exclude(status=Trip.Status.DELETED).exclude(status=Trip.Status.DRAFT)

        # Если пользователь не суперпользователь, фильтруем по его поездкам
        if not request.user.is_superuser:
            trips = trips.filter(user=request.user)  # Предполагается, что в модели Trip есть поле user (ForeignKey)

        # Фильтрация по статусу, если передан в запросе
        status = request.query_params.get('status')
        if status:
            trips = trips.filter(status=status.upper())

        # Фильтрация по дате, если переданы даты
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            trips = trips.filter(created_at__range=[start_date, end_date])

        # Сериализация данных
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

class TripDetailAPIView(APIView):
    """
    GET: Детали заявки
    PUT: Обновление заявки
    DELETE: Удаление заявки
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='get')
    @method_permission_classes((is_authenticated,))
    def get(self, request: Request, trip_id: int) -> Response:
        """
        GET /api/trips/<id>/
        """
        trip = get_object_or_404(Trip, id=trip_id)
        serializer = TripDetailSerializer(trip)
        return Response(serializer.data)

    @swagger_auto_schema(method='put')
    @method_permission_classes((is_authenticated,))
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

    @swagger_auto_schema(method='delete')
    @method_permission_classes((is_authenticated,))
    def delete(self, request: Request, trip_id: int) -> Response:
        """
        DELETE /api/trips/<id>/
        """
        trip = get_object_or_404(Trip, id=trip_id)
        trip.status = Trip.Status.DELETED
        trip.save()
        return Response({"detail": "Trip marked as deleted"},
                        status=status.HTTP_204_NO_CONTENT)


class RouteDraftTripAPIView(APIView):
    """
    POST: Добавление маршрута в заявку-черновик.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='post')
    @method_permission_classes((is_authenticated,))
    def post(self, request: Request, route_id: int) -> Response:
        """
        POST /api/routes/<id>/trip/
        Добавление маршрута в заявку-черновик.
        Если черновик отсутствует, он создаётся.
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "User not authenticated"},
                            status=status.HTTP_403_FORBIDDEN)

        # Получаем или создаём черновик для пользователя
        trip = get_trip(user)

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


class TripFormAPIView(APIView):
    """
    PUT /trips/<id>/form/
    Формирование заявки создателем.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='post')
    @method_permission_classes((is_authenticated,))
    def post(self, request: Request, trip_id: int) -> Response:
        """
        Формирование заявки создателем.
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "User not authenticated"},
                            status=status.HTTP_403_FORBIDDEN)

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
    """
        POST /trips/<id>/finish/
        Завершение или отклонение заявки модератором.
        action: "finish" для завершения, "dismiss" для отклонения.
        """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='post')
    @method_permission_classes((is_moderator,))
    def post(self, request: Request, trip_id: int) -> Response:
        user = request.user

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

        # Завершаем или отклоняем поездку
        trip.status = Trip.Status.FINISHED if action == "finish" else Trip.Status.DISMISSED
        trip.ended_at = timezone.now() if action == "finish" else None
        trip.moderator = user

        # При завершении рассчитываем общую стоимость
        if action == "finish":
            routes = RouteTrip.objects.filter(trip=trip)
            total_duration = routes.aggregate(
                duration_total=models.Sum("duration")
            )["duration_total"] or 0
            trip.duration_total = total_duration

            qr_code = generate_trip_qr(trip, routes, user)
            trip.qr = qr_code

        trip.save()

        serializer = TripSerializer(trip)

        response_data = serializer.data

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )


class RouteTripAPIView(APIView):
    """
        DELETE: Удаление маршрута из заявки.
        PUT: Изменение маршрута в заявке.
        """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='delete')
    @method_permission_classes((is_authenticated,))
    def delete(self, request: Request, route_id: int) -> Response:
        """
        DELETE /api/routes/<id>/trip/
        Удаление маршрута из черновика.
        """
        user = request.user
        if user.is_authenticated:
            trip = Trip.objects.filter(user=user, status=Trip.Status.DRAFT).first()
            if not trip:
                return Response({"error": "No draft trip found"},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "User not authenticated"},
                            status=status.HTTP_403_FORBIDDEN)

        route = get_object_or_404(Route, id=route_id)

        route_trip = RouteTrip.objects.filter(trip=trip, route=route).first()
        if not route_trip:
            return Response({"error": "Route not found in the draft trip"},
                            status=status.HTTP_404_NOT_FOUND)

        route_trip.delete()
        return Response({"detail": "Route removed from the draft trip"},
                        status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='put')
    @method_permission_classes((is_authenticated,))
    def put(self, request: Request, route_id: int) -> Response:
        """
        PUT /api/routes/<id>/trip/
        Изменение данных маршрута в черновике (free, order).
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "User not authenticated"}, status=status.HTTP_403_FORBIDDEN)

        trip = Trip.objects.filter(user=user, status=Trip.Status.DRAFT).first()
        if not trip:
            return Response({"error": "No draft trip found"}, status=status.HTTP_404_NOT_FOUND)

        route = get_object_or_404(Route, id=route_id)
        route_trip = RouteTrip.objects.filter(trip=trip, route=route).first()
        if not route_trip:
            return Response({"error": "Route not found in the draft trip"}, status=status.HTTP_404_NOT_FOUND)

        # Обновление поля free, если оно передано
        free = request.data.get("free")
        if free is not None:
            route_trip.free = free

        # Обновление поля order, если оно передано
        order = request.data.get("order")
        if order is not None:
            try:
                new_order = int(order)
            except ValueError:
                return Response({"error": "Invalid order value"}, status=status.HTTP_400_BAD_REQUEST)

            # Проверяем, что новый порядок в допустимых пределах
            route_count = RouteTrip.objects.filter(trip=trip).count()
            if new_order < 1 or new_order > route_count:
                return Response(
                    {"error": f"Order must be between 1 and {route_count}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Если порядок изменился, пересчитываем другие маршруты
            if route_trip.order != new_order:
                # Сдвигаем другие маршруты
                if new_order < route_trip.order:
                    # Сдвигаем маршруты вниз (увеличиваем порядок)
                    RouteTrip.objects.filter(
                        trip=trip, order__gte=new_order, order__lt=route_trip.order
                    ).update(order=models.F("order") + 1)
                elif new_order > route_trip.order:
                    # Сдвигаем маршруты вверх (уменьшаем порядок)
                    RouteTrip.objects.filter(
                        trip=trip, order__gt=route_trip.order, order__lte=new_order
                    ).update(order=models.F("order") - 1)

                # Устанавливаем новый порядок для текущего маршрута
                route_trip.order = new_order

        # Сохраняем изменения
        route_trip.save()

        return Response(
            {
                "detail": "Route trip updated",
                "route_id": route.id,
                "free": route_trip.free,
                "order": route_trip.order,
            },
            status=status.HTTP_200_OK,
        )


class UserRegistrationAPIView(APIView):
    """
    POST /users/register/
    Регистрация нового пользователя.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request, format=None):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            password = serializer.validated_data['password']
            serializer.validated_data['password'] = make_password(password)

            user = User(**{key: value for key, value in serializer.validated_data.items() if
                           key not in ['groups', 'user_permissions']})
            user.save()

            groups = serializer.validated_data.get('groups', None)
            if groups:
                user.groups.set(groups)

            user_permissions = serializer.validated_data.get('user_permissions', None)
            if user_permissions:
                user.user_permissions.set(user_permissions)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserUpdateAPIView(APIView):
    """
    PUT /users/update/
    Изменение данных пользователя.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]


    @swagger_auto_schema(request_body=UserUpdateSerializer)
    @method_permission_classes((is_authenticated,))
    def put(self, request, format=None):
        user = get_object_or_404(User, username=request.user)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserAuthAPIView(APIView):
    """
        POST /users/auth/
        Авторизация.
        """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []
    @swagger_auto_schema(request_body=UserAuthSerializer)
    def post(self, request, format=None):
        if not request.data.get('username') or not request.data.get('password'):
            return Response({"error": "Не указаны данные для авторизации"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=request.data['username'], password=request.data['password'])
        if user is not None:
            login(request, user)
            random_key = uuid.uuid4().hex
            for key in session_storage.scan_iter():
                if session_storage.get(key).decode('utf-8') == user.username:
                    session_storage.delete(key)
            session_storage.set(random_key, user.username)
            response_data = {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_superuser": user.is_superuser,
            }
            response = Response(response_data)
            response.set_cookie('session_id', random_key)
            return response
        return Response({"error": "Неверный логин или пароль"}, status=status.HTTP_400_BAD_REQUEST)


class UserDeauthAPIView(APIView):
    """
        POST /users/deauth/
        Деавторизация.
        """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [is_authenticated]

    @swagger_auto_schema(method='post')
    def post(self, request: Request) -> Response:
        session_id = request.COOKIES.get('session_id')
        session_storage.delete(session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

class AttributeAPIView(APIView):
    """
    GET: Получение списка атрибутов объекта.
    POST: Добавление нового атрибута к объекту.
    DELETE: Удаление атрибута объекта.
    PUT: Редактирование значения атрибута объекта.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(method='get')
    def get(self, request, object_id: int) -> Response:
        """
        GET /api/routes/<id>/attributes/
        """
        route = get_object_or_404(Route, id=object_id)

        # Получаем все связанные атрибуты маршрута
        attributes = route.attribute_values.select_related("attribute").all()

        # Преобразуем в JSON-ответ
        response_data = [
            {"name": attr.attribute.name, "value": attr.value}
            for attr in attributes
        ]

        return Response({"attributes": response_data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(method='post')
    @method_permission_classes((is_moderator,))
    def post(self, request: Request, object_id: int) -> Response:
        """
        POST /api/routes/<id>/attributes/
        """
        route = get_object_or_404(Route, id=object_id)
        attribute_name = request.data.get("attribute_name")
        attribute_value = request.data.get("attribute_value")

        if not attribute_name or attribute_value is None:
            return Response(
                {"error": "Both attribute name and value are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        attribute, created = Attribute.objects.get_or_create(name=attribute_name)

        route_attribute, created = RouteAttributeValue.objects.get_or_create(
            route=route, attribute=attribute, defaults={"value": attribute_value}
        )

        if not created:
            route_attribute.value = attribute_value
            route_attribute.save(update_fields=["value"])
        other_routes = Route.objects.exclude(id=object_id)
        existing_attributes = RouteAttributeValue.objects.filter(
            route__in=other_routes, attribute=attribute
        ).values_list("route_id", flat=True)

        new_route_attrs = [
            RouteAttributeValue(route=r, attribute=attribute, value="")
            for r in other_routes if r.id not in existing_attributes
        ]
        RouteAttributeValue.objects.bulk_create(new_route_attrs)

        return Response(
            {"detail": f"Attribute '{attribute_name}' set successfully."},
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(method='delete')
    @method_permission_classes((is_moderator,))
    def delete(self, request: Request, object_id: int) -> Response:
        """
        DELETE /api/routes/<id>/attributes/
        """
        route = get_object_or_404(Route, id=object_id)
        attribute_name = request.data.get("attribute_name")

        if not attribute_name:
            return Response({"error": "Attribute name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Найти атрибут
        attribute = Attribute.objects.filter(name=attribute_name).first()
        if not attribute:
            return Response({"error": f"Attribute '{attribute_name}' not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # Найти связь маршрута и атрибута
        route_attribute = RouteAttributeValue.objects.filter(route=route, attribute=attribute).first()
        if not route_attribute:
            return Response({"error": f"Attribute '{attribute_name}' not found for this route."},
                            status=status.HTTP_404_NOT_FOUND)

        # Удалить связь маршрута и атрибута
        route_attribute.delete()

        return Response({"detail": f"Attribute '{attribute_name}' removed successfully."},
                        status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='put')
    @method_permission_classes((is_moderator,))
    def put(self, request: Request, object_id: int) -> Response:
        """
        PUT /api/routes/<id>/attributes/
        """
        route = get_object_or_404(Route, id=object_id)
        attribute_name = request.data.get("attribute_name")
        new_value = request.data.get("new_value")

        if not attribute_name or new_value is None:
            return Response({"error": "Both attribute name and new value are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, существует ли атрибут в системе
        attribute = Attribute.objects.filter(name=attribute_name).first()
        if not attribute:
            return Response({"error": f"Attribute '{attribute_name}' not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # Проверяем, существует ли этот атрибут у маршрута
        route_attribute = RouteAttributeValue.objects.filter(route=route, attribute=attribute).first()

        if not route_attribute:
            return Response({"error": f"Attribute '{attribute_name}' not found for this route."},
                            status=status.HTTP_404_NOT_FOUND)

        if new_value == "":
            # Если новое значение пустое — удаляем атрибут
            route_attribute.delete()
            return Response({"detail": f"Attribute '{attribute_name}' removed due to empty value."},
                            status=status.HTTP_204_NO_CONTENT)
        else:
            # Обновляем значение атрибута
            route_attribute.value = new_value
            route_attribute.save(update_fields=["value"])
            return Response({"detail": f"Attribute '{attribute_name}' updated successfully."},
                            status=status.HTTP_200_OK)
class UserWork(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [is_authenticated | is_guest]
        elif self.request.method == 'POST':
            permission_classes = [is_admin | is_moderator | is_authenticated]
        elif self.request.method in ['PUT', 'DELETE']:
            permission_classes = [is_admin | is_moderator | is_authenticated]
        else:
            permission_classes = [is_admin]

        return [permission() for permission in permission_classes]