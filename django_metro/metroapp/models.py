from django.contrib.auth.models import User
from django.db import models


class Route(models.Model):
    origin = models.CharField(max_length=256)
    destination = models.CharField(max_length=256)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    thumbnail = models.URLField(null=True, blank=True)
    price = models.IntegerField()

    class Meta:
        db_table = "routes"
        constraints = [
            models.UniqueConstraint(
                fields=['origin', 'destination', 'description'],
                name="unique constraint"
            )
        ]


class Trip(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        FORMED = "FORMED"
        DELETED = "DELETED"
        FINISHED = "FINISHED"
        DISMISSED = "DISMISSED"

    status = models.CharField(max_length=32, choices=Status.choices,
                              default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    owner = models.CharField(max_length=128, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name="trips", null=True, blank=True)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name="moderator",
                                  null=True, blank=True)

    formed_at = models.DateTimeField(null=True, blank=True)  # user action
    ended_at = models.DateTimeField(null=True, blank=True)  # moderator action

    price_total = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "trips"


class RouteTrip(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    free = models.BooleanField(default=False)

    class Meta:
        unique_together = (("route", "trip"),)
