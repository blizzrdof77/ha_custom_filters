"""Constants for the custom_filters integration."""

DOMAIN = "custom_filters"

__version__ = "0.9.35"

COMPONENT_NAME = "Custom filters for Jinja2 templates"
COMPONENT_TITLE = "Custom Jinja Filters"

ENABLED_FILTERS = [
    'replace_all',
    'is_defined',
    'get_type',
    'is_type',
    'is_numeric',
    'inflate',
    'deflate',
    'deflate_and_base64_encode',
    'decode_base64_and_inflate',
    'decode_valetudo_map',
    'urldecode',
    'strtolist',
    'listify',
    'get_index',
    'grab',
    'reach',
    'ternary',
    'shuffle',
    'to_ascii_json',
    'sortnat',
    'contains_all',
    'contains_any'
]
