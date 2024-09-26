from django.contrib import admin
from .models import Menu, MenuItem

class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [MenuItemInline]

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'menu', 'parent', 'url', 'icon']
    list_filter = ['menu', 'parent']
    search_fields = ['name', 'url', 'icon']
    filter_horizontal = ['visibility']  # Display the visibility field in admin with multiple selection

    # Optional: To make visibility field show a helpful label in the admin
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['visibility'].help_text = "Select the groups that can view this menu item. Leave empty to make it visible to everyone."
        return form
