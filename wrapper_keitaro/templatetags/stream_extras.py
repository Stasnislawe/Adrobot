from django import template

register = template.Library()


@register.filter
def sum_active_weights(stream_offers):
    """Сумма весов активных офферов"""
    return sum(so.weight for so in stream_offers if so.is_active)


@register.filter
def sum_pinned_weights(stream_offers):
    """Сумма весов закреплённых активных офферов"""
    return sum(so.weight for so in stream_offers if so.is_active and so.pinned)