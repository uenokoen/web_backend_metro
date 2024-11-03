from django.db import models


class Route(models.Model):
    origin = models.CharField(max_length=256)
    destination = models.CharField(max_length=256)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    thumbnail = models.URLField(null=True, blank=True)
    price = models.IntegerField()

    class Meta:
        db_table="routes"
        constraints = [
            models.UniqueConstraint(
                fields=['origin', 'destination', 'description'], 
                name="unique constraint"
            )
        ]


class Order(models.Model):

    class Status(models.TextChoices):
            DRAFT = "DRAFT"
            FORMED = "FORMED"
            DELETED = "DELETED"
            FINISHED = "FINISHED"
            DISMISSED = "DISMISSED"

    status = models.CharField(max_length=32, choices=Status.choices, 
                              default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    owner = models.CharField(max_length=128)

    formed_at = models.DateTimeField(null=True) # user action
    ended_at = models.DateTimeField(null=True)  # moderator action

    class Meta:
        db_table = "orders"


class RouteOrder(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)