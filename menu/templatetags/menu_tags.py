from django import template
from menu.models import Menu

register = template.Library()

@register.inclusion_tag('menu/menu_template.html')
def load_menu():
    menus = Menu.objects.prefetch_related('items').all()
    return {'menus': menus}
