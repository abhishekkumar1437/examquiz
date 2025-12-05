from django import template

register = template.Library()


@register.filter
def format_time(seconds):
    """Format seconds into minutes and seconds"""
    if not seconds:
        return "-"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@register.filter
def minutes_only(seconds):
    """Get minutes from seconds"""
    if not seconds:
        return "-"
    return seconds // 60

