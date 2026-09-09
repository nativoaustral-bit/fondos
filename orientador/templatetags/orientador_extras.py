from django import template

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def format_money(val, moneda='CLP'):
    if val is None or val == '':
        return 'Monto por confirmar'
    try:
        num = float(val)
        if moneda == 'CLP':
            return f"${num:,.0f}".replace(',', '.')
        return f"{num:g} {moneda}"
    except (ValueError, TypeError):
        return str(val)
