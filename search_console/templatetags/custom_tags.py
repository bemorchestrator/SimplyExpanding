from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def delta_css_class(value, field):
    # Returns 'text-green-500' or 'text-red-500' based on the value and whether increase is positive
    if value is None or value == '':
        return ''
    try:
        value = float(value)
    except (ValueError, TypeError):
        return ''
    increase_positive_fields = {
        'clicks_change': True,
        'impressions_change': True,
        'ctr_change': True,
        'position_change': False,
    }
    is_positive = increase_positive_fields.get(field, True)
    if is_positive:
        if value > 0:
            return 'text-green-500'
        elif value < 0:
            return 'text-red-500'
    else:
        if value < 0:
            return 'text-green-500'
        elif value > 0:
            return 'text-red-500'
    return ''
