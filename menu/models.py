from django.contrib.auth.models import Group
from django.db import models

class Menu(models.Model):
    """
    Represents a top-level menu. Each menu can have multiple MenuItems.
    The 'position' field allows ordering of menus.
    """
    name = models.CharField(max_length=100)
    position = models.PositiveIntegerField(default=0, blank=False, null=False)  # Position for sorting

    class Meta:
        ordering = ['position']  # Default ordering based on position

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """
    Represents an item within a menu. MenuItems can have child items (submenus).
    The 'position' field allows ordering of menu items.
    """
    menu = models.ForeignKey(Menu, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200, blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)  # Optional icon for menu item
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.CASCADE)
    visibility = models.ManyToManyField(Group, blank=True, help_text="Select which groups can see this menu item. Leave empty for everyone.")
    position = models.PositiveIntegerField(default=0, blank=False, null=False)  # Position for sorting

    class Meta:
        ordering = ['menu', 'position']  # Order by menu first, then by position within that menu

    def __str__(self):
        return f"{self.name} (Menu: {self.menu.name})"

    def children(self):
        """
        Returns the child items of the current MenuItem.
        """
        return self.children.all().order_by('position')
