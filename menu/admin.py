from django.contrib import admin
from .models import Menu, MenuItem

class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ['name', 'url', 'icon', 'parent', 'position', 'visibility']  # Add position to inline fields
    ordering = ['position']  # Ensure inline items are ordered by position


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'position']  # Add position to list display
    list_editable = ['position']  # Make position editable directly in the admin list view
    ordering = ['position']  # Ensure menus are ordered by position
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'menu', 'parent', 'url', 'icon', 'position']  # Add position to list display
    list_editable = ['position']  # Make position editable directly in the admin list view
    list_filter = ['menu', 'parent']
    search_fields = ['name', 'url', 'icon']
    filter_horizontal = ['visibility']  # Display the visibility field in admin with multiple selection
    ordering = ['menu', 'position']  # Ensure items are ordered by menu first, then by position

    # Optional: To make visibility field show a helpful label in the admin
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['visibility'].help_text = "Select the groups that can view this menu item. Leave empty to make it visible to everyone."
        return form
