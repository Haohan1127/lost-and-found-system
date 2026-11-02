from django.db import models


class Campus(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=60)


class Category(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=60)
    sort_order = models.PositiveIntegerField(default=0)


class Location(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT)
    name = models.CharField(max_length=60)
    sort_order = models.PositiveIntegerField(default=0)
