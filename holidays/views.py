# holidays/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Holiday
from .forms import HolidayForm
from django.contrib import messages
import calendar

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
            # Get the cleaned data
            is_recurring = form.cleaned_data.get('is_recurring')
            recurring_month = request.POST.get('recurring_month')
            recurring_day = request.POST.get('recurring_day')
            
            # Check if the holiday is recurring
            if is_recurring:
                # Ensure both recurring month and day are provided
                if not recurring_month or not recurring_day:
                    form.add_error(None, 'Both recurring month and day must be provided for recurring holidays.')
                else:
                    # Save the holiday as a recurring holiday without a date
                    holiday = form.save(commit=False)
                    holiday.date = None  # Clear the date since it's recurring
                    holiday.recurring_month = recurring_month
                    holiday.recurring_day = recurring_day
                    holiday.save()
                    messages.success(request, 'Recurring holiday added successfully.')
                    return redirect('holiday_list')
            else:
                # Non-recurring holiday, save as normal
                form.save()
                messages.success(request, 'Holiday added successfully.')
                return redirect('holiday_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = HolidayForm()

    # Provide the months for the dropdown
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    return render(request, 'holidays/add_holiday.html', {'form': form, 'months': months})


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
