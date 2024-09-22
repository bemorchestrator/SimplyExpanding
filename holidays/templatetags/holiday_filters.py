from django import template
import calendar

register = template.Library()

@register.filter
def get_month_name(month_number):
    """Takes an integer month and returns the month name."""
    if month_number and 1 <= month_number <= 12:
        return calendar.month_name[month_number]
    return ''
