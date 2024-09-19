# holidays/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Holiday
from .forms import HolidayForm
from django.contrib import messages

@login_required
def holiday_list(request):
    """
    Display a list of all holidays with options to add or delete.
    """
    holidays = Holiday.objects.all().order_by('date')
    return render(request, 'holidays/holiday_list.html', {'holidays': holidays})

@login_required
def add_holiday(request):
    """
    Handle the creation of a new holiday.
    """
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Holiday added successfully.')
            return redirect('holiday_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = HolidayForm()
    return render(request, 'holidays/add_holiday.html', {'form': form})

@login_required
def delete_holiday(request, holiday_id):
    """
    Handle the deletion of a holiday.
    """
    holiday = get_object_or_404(Holiday, id=holiday_id)
    if request.method == 'POST':
        holiday.delete()
        messages.success(request, 'Holiday deleted successfully.')
        return redirect('holiday_list')
    return render(request, 'holidays/delete_holiday.html', {'holiday': holiday})
