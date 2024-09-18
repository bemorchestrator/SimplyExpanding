from django.shortcuts import render
from .models import Menu

def load_menu(request):
    menus = Menu.objects.prefetch_related('items').all()
    return {'menus': menus}
