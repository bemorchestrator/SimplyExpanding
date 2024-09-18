from .models import Menu

def menu_context(request):
    menus = Menu.objects.prefetch_related('items').all()
    return {'menus': menus}
