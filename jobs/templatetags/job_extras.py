from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary and key:
        try:
            return dictionary.get(key)
        except (AttributeError, TypeError):
            return None
    return None

@register.filter
def match_score_class(score):
    """Return CSS class based on match score"""
    try:
        score = float(score) if score else 0
        if score >= 80:
            return 'bg-success'
        elif score >= 60:
            return 'bg-warning'
        else:
            return 'bg-secondary'
    except (ValueError, TypeError):
        return 'bg-secondary'

@register.filter
def default_if_none(value, default):
    """Return default value if input is None"""
    return value if value is not None else default
