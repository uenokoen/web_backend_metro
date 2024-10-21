from django.db import models


class Route(models.Model):
    origin = models.CharField(max_length=256)
    destination = models.CharField(max_length=256)
    price = models.IntegerField()
    thumbnail = models.URLField()
    description = models.TextField()

class OrderState(models.Model):
    state = models.CharField(max_length=64, unique=True)

class Order(models.Model):
    routes = models.ManyToManyField(Route)
    state = models.ForeignKey(OrderState, on_delete=models.DO_NOTHING, default=0)
