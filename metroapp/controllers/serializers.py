from django.contrib.auth.models import User
from rest_framework import serializers

from metroapp.models import Route, Trip, RouteTrip


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"
        read_only_fields = ["id", "thumbnail", "is_active"]

class RoutePicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['thumbnail']


class RouteTripNestedSerializer(serializers.ModelSerializer):
    route = RouteSerializer()

    class Meta:
        model = RouteTrip
        fields = ["route", "free","order","duration"]


class TripSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = "__all__"
        read_only_fields = ["user", "moderator", "status", "price_total"]

    def get_user(self, obj):
        return obj.user.username if obj.user else None

    def get_moderator(self, obj):
        return obj.moderator.username if obj.moderator else None

class DraftTripSerializer(serializers.ModelSerializer):
    route_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ['id', 'route_count']

    def get_route_count(self, obj):
        # Подсчет количества связанных маршрутов
        return obj.routetrip_set.count()

class TripDetailSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()
    routetrip_set = RouteTripNestedSerializer(many=True)

    class Meta:
        model = Trip
        fields = "__all__"

    def get_user(self, obj):
        return obj.user.username

    def get_moderator(self, obj):
        return obj.moderator.username if obj.moderator else None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя.
    """
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def create(self, validated_data: dict) -> User:
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для изменения данных пользователя с необязательной сменой пароля.
    """
    new_password = serializers.CharField(write_only=True, required=False, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "new_password", "confirm_password")

    def validate(self, data):
        # Если указан новый пароль, нужно проверить подтверждение
        if data.get("new_password") or data.get("confirm_password"):
            if data.get("new_password") != data.get("confirm_password"):
                raise serializers.ValidationError({"confirm_password": "Пароли не совпадают."})
        return data

    def update(self, instance, validated_data):
        # Обновление обычных полей пользователя
        instance.username = validated_data.get("username", instance.username)
        instance.email = validated_data.get("email", instance.email)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)

        # Смена пароля, если он был указан
        if validated_data.get("new_password"):
            instance.set_password(validated_data["new_password"])

        instance.save()
        return instance

class UserAuthSerializer(serializers.ModelSerializer):
    """
    Сериализатор для авторизации/деавторизации пользователя.
    """
    class Meta:
        model = User
        fields = ("username","password")