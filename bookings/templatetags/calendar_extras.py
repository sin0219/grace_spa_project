from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """辞書から値を取得するフィルター"""
    if dictionary and key:
        return dictionary.get(key, [])
    return []