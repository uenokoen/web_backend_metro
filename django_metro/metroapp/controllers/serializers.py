from django.contrib.auth.models import User
from rest_framework import serializers

from metroapp.models import Route, Trip, RouteTrip


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"
        read_only_fields = ["id", "thumbnail", "is_active"]


class RouteTripNestedSerializer(serializers.ModelSerializer):
    route = RouteSerializer()

    class Meta:
        model = RouteTrip
        fields = ["route", "free"]


class TripSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = "__all__"
        read_only_fields = ["user", "moderator", "status", "price_total"]

    def get_user(self, obj):
        return obj.user.username

    def get_moderator(self, obj):
        return obj.moderator.username if obj.moderator else None


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
    Сериализатор для изменения данных пользователя.
    """
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")