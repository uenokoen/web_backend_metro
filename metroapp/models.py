import random

from django.contrib.auth.models import User
from django.db import models


class Route(models.Model):
    origin = models.CharField(max_length=256, verbose_name="Пункт отправления")
    destination = models.CharField(max_length=256, verbose_name="Пункт назначения")
    description = models.TextField(verbose_name="Описание маршрута")
    is_active = models.BooleanField(default=True, verbose_name="Активность")
    thumbnail = models.URLField(null=True, blank=True, verbose_name="Миниатюра")
    price = models.IntegerField(verbose_name="Цена")

    class Meta:
        db_table = "routes"
        verbose_name = "Маршрут"
        verbose_name_plural = "Маршруты"
        constraints = [
            models.UniqueConstraint(
                fields=['origin', 'destination'],
                name="unique constraint"
            )
        ]

    def __str__(self):
        return f"{self.origin} → {self.destination}"


class Attribute(models.Model):
    name = models.CharField(max_length=256, verbose_name="Название атрибута")
    description = models.TextField(null=True, blank=True, verbose_name="Описание атрибута")

    class Meta:
        db_table = "attributes"
        verbose_name = "Атрибут"
        verbose_name_plural = "Атрибуты"

    def __str__(self):
        return f"{self.name}"

class RouteAttributeValue(models.Model):
    route = models.ForeignKey(Route, related_name="attribute_values", on_delete=models.CASCADE, verbose_name="Маршрут")
    attribute = models.ForeignKey(Attribute, related_name="route_values", on_delete=models.CASCADE, verbose_name="Атрибут")
    value = models.TextField(verbose_name="Значение атрибута")

    class Meta:
        db_table = "route_attribute_values"
        verbose_name = "Значение атрибута маршрута"
        verbose_name_plural = "Значения атрибутов маршрутов"
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'attribute'],
                name="unique_route_attribute"
            )
        ]

    def __str__(self):
        return f"{self.attribute} - {self.value} у {self.route}"

class Trip(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        FORMED = "FORMED", "Сформировано"
        DELETED = "DELETED", "Удалено"
        FINISHED = "FINISHED", "Завершено"
        DISMISSED = "DISMISSED", "Отклонено"

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус"
    )
    name = models.CharField(max_length=256, verbose_name="Название заявки",null=True,blank=True)
    description = models.TextField(null=True, blank=True, verbose_name="Описание заявки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    owner = models.CharField(max_length=128, null=True, blank=True, verbose_name="Владелец")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="trips",
        null=True,
        blank=True,
        verbose_name="Пользователь"
    )
    moderator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="moderator",
        null=True,
        blank=True,
        verbose_name="Модератор"
    )
    formed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата формирования")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    qr = models.TextField(null=True, blank=True,verbose_name= "QR-код")
    duration_total = models.PositiveIntegerField(verbose_name="Общее время поездки (минуты)", null=True, blank=True)
    class Meta:
        db_table = "trips"
        verbose_name = "Поездка"
        verbose_name_plural = "Поездки"

    def __str__(self):
        return f"{self.name} - {self.status}"

class RouteTrip(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, verbose_name="Маршрут")
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name="Поездка")
    order = models.PositiveIntegerField(verbose_name="Порядок маршрута",null=True,blank=True)
    free = models.BooleanField(default=False, verbose_name="Бесплатно")
    duration = models.PositiveIntegerField(verbose_name="Время проезда (минуты)", null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.duration is None:
            self.duration = random.randint(30, 300)
        if self.order is None:
            super().save(*args, **kwargs)
            route_trips = RouteTrip.objects.filter(trip=self.trip).order_by("duration")
            for index, route_trip in enumerate(route_trips, start=1):
                if route_trip.order != index:
                    route_trip.order = index
                    route_trip.save(update_fields=["order"])
        else:
            super().save(*args, **kwargs)

    class Meta:
        unique_together = (("route", "trip"),)
        verbose_name = "Связь маршрута с поездкой"
        verbose_name_plural = "Связи маршрутов с поездками"
        ordering = ["order"]

    def __str__(self):
        return f"{self.trip} - {self.route}"