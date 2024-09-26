from django.contrib.auth.models import Group
from django.db import models

class Menu(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200, blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)  # Field to store icon class
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.CASCADE)
    
    # New field to control visibility by user group
    visibility = models.ManyToManyField(Group, blank=True, help_text="Select which groups can see this menu item. Leave empty for everyone.")

    def __str__(self):
        return self.name
