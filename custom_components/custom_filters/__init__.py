"""Support custom filters for jinja2 templating"""
import ast
import base64
import logging
import json
import numbers
import re
import urllib.parse
import zlib

# import jinja2

from random import Random
from operator import attrgetter
from natsort import natsorted, ns

from homeassistant.helpers import template
# from homeassistant.util.yaml import loader

from .const import *

_LOGGER = logging.getLogger(__name__)

_TemplateEnvironment = template.TemplateEnvironment

# jinja = jinja2.Environment(loader=loader)


# -- REPLACE ALL
def replace_all(value, find, replace=''):
    """Replace all provided values with replacement value(s)"""
    find_all = find if isinstance(find, (list)) else [find]
    for i in find_all:
        rep = replace if not isinstance(replace, (list)) else replace[find.index(i)]
        value = value.replace(i, rep)
    return value


# -- IS DEFINED
def is_defined(value):
    """Check if a variable is defined by it's string name"""
    try:
        globals()[value]
    except NameError:
        return False
    return True


# -- GET TYPE
def get_type(value):
    """Return the object type as a string"""
    return type(value).__name__


# -- IS TYPE
def is_type(value, typeof):
    """Check if a value is of given type"""
    if str(typeof) == typeof:
        typeofobj = typeof
    elif isinstance(typeof, type):
        typeofobj = getattr(typeof, '__name__', False)
    else:
        typeofobj = False
    if not isinstance(typeofobj, str):
        return None
    typeofobj = typeofobj.lower()
    val_type = type(value).__name__
    check_type = (
        typeofobj.lower()
        .replace('boolean', 'bool')
        .replace('integer', 'int')
        .replace('double', 'float')
        .replace('array', 'list')
        .replace('string', 'str')
        .replace('text', 'str')
        .replace('dictionary', 'dict')
        .replace('mapping', 'dict')
        .replace('nonetype', 'none')
        .replace('none', 'NoneType')
        .replace('null', 'NoneType')
    )
    if check_type == 'number':
        passchk = val_type in ['int', 'float', 'complex']
    elif check_type == 'sequence':
        passchk = val_type in ['list', 'tuple', 'range']
    elif check_type == 'json':
        passchk = val_type in ['dict', 'list']
    else:
        passchk = val_type == check_type
    return passchk


# -- IS NUMERIC
def is_numeric(value, strict=False):
    """Check if a variable has a numeric value"""
    result = (isinstance(value, numbers.Number))
    if (result or strict):
        return(result)
    else:
        try:
            if (is_type(value, 'str') and "," in value):
                setval = float(re.sub("([\d])[,]([\d])", "\\1\\2", value))
            else:
                setval = float(value)
            return True
        except ValueError:
            return False


# -- INFLATE
def inflate(value):
    """Inflates/compresses a value"""
    return zlib.compress(value.encode("utf-8"))


# -- DEFLATE
def deflate(value):
    """Deflates/decompresses a value"""
    return zlib.decompress(value)


# -- DECODE BASE64 AND INFLATE
def decode_base64_and_inflate(value):
    """Decodes and inflates a value"""
    data = base64.b64decode(value)
    return zlib.decompress(data).decode("utf-8")


# -- DEFLATE AND BASE64 ENCODE
def deflate_and_base64_encode(value):
    """Deflates and encodes a value"""
    data = zlib.compress(value.encode("utf-8"))
    return base64.b64encode(data).decode("utf-8")


# -- DECODE VALETUDO MAP
def decode_valetudo_map(value):
    """Currently equivalent to deflate_and_base64_encode."""
    return decode_base64_and_inflate(value)


# -- URL DECODE
def urldecode(value):
    """Remove quotes from a value"""
    return urllib.parse.unquote(value)


# -- STRTOLIST
def strtolist(value, delim=","):
    """Convert a value to a list"""
    obj_res = re.sub(r"([\s]?)+(['\"])+([\s]?)", "\\2", value.strip((r"[]"))).strip()
    if len(obj_res) == 0:
        obj_res = []
    else:
        if delim != ",":
            obj_res = obj_res.replace(delim, ",")
        obj_res = "[" + obj_res.strip("[]") + "]"
        try:
            obj_res = ast.literal_eval(obj_res)
        except ValueError:
            obj_res = obj_res.split(",")
    return obj_res


# -- LISTIFY
def listify(value, delim=","):
    """Convert a value or non-list/dict into a list/dict"""
    if isinstance(value, (list, dict)):
        obj_res = value
    else:
        obj_res = str(value).strip()
        # Determine if it's a dict, list, or implied list
        if obj_res.startswith('{') and obj_res.endswith('}'):
            obj_res = ast.literal_eval(obj_res)
        else:
            if not obj_res.startswith('['):
                obj_res = "[" + obj_res
            if not obj_res.endswith(']'):
                obj_res = obj_res + "]"
            # Convert to list or return the dict
            if obj_res.startswith('[') and obj_res.endswith(']'):
                if obj_res == "[]":
                    obj_res = []
                else:
                    obj_res = strtolist(obj_res.replace(
                        "[ ", "[").replace(" ]", "]").replace(delim + " ", delim))
    return obj_res


# -- GET INDEX
def get_index(value, key, fallback=False):
    """Return the numeric index of a list or dict item"""
    # Normalize the list
    if isinstance(value, dict):
        list_obj = list(value.keys())
    elif isinstance(value, list):
        list_obj = value
    else:
        list_obj = listify(value)
    # Check if index exists
    try:
        index_value = list_obj.index(key)
    except ValueError:
        index_value = fallback
    return index_value


# -- GRAB
def grab(value, key=0, fallback=""):
    """Get a list/dict item by key, with optional fallback"""
    # Normalize the object
    if isinstance(value, str):
        value = listify(value)
    # Normalize the key based on object type
    if isinstance(value, dict):
        if isinstance(key, int):
            try:
                key = value[list(value)[key]]
            except IndexError:
                return fallback
        elif not isinstance(key, str):
            return fallback
    elif isinstance(value, list):
        if not isinstance(key, int):
            return fallback
    else:
        return fallback
    # Check if key/value exists
    try:
        my_val = value[key]
    except IndexError:
        return fallback
    return my_val


# -- REACH
def reach(value, keypath, fallback=""):
    """Get a dict item by full path of key(s), with optional fallback"""
    res = {"found": True, "level": value, "value": False}
    keys = keypath.split('.')
    if isinstance(value, (dict, list)):
        for key in keys:
            if res["found"] is True:
                try:
                    res["level"] = res["level"][key]
                except KeyError:
                    res["found"] = False
                    return fallback
            else:
                return fallback
    else:
        return fallback
    return res["level"]


# -- TERNARY
def ternary(value, true_val, false_val, none_val=None):
    """Ternary evaluation fo True, False, or None values"""
    # value ? true_val : false_val
    if value is None and none_val is not None:
        res = none_val
    elif bool(value):
        res = true_val
    else:
        res = false_val
    return res


# -- RANDOMIZE/SHUFFLE LIST
def shuffle(value):
    """Shuffle list"""
    try:
        value = listify(value)
        rand = Random()
        rand.shuffle(value)
    except Exception:
        pass
    return value


# -- TO ASCII JSON
def to_ascii_json(value):
    """Convert value to ASCII JSON"""
    return json.dumps(value, ensure_ascii=False)


# -- NATURAL SORTING
def sortnat(value, reverse=False, ignore_case=True, attribute=None):
    """Identifies numbers anywhere in a string and sorts them naturally"""
    if not ignore_case:
        alg = ns.LOWERCASEFIRST
    else:
        alg = ns.IGNORECASE
    if attribute:
        key = attrgetter(attribute)
    else:
        key = None
    return natsorted(value, reverse=reverse, alg=alg, key=key)


# -- CONTAINS ALL
def contains_all(value, matches):
    """Check if value contains all of the provided sub-values"""
    find_all = matches if isinstance(matches, (list)) else [matches]
    for i in find_all:
        if i not in value:
            return False
    return True


# -- CONTAINS ANY
def contains_any(value, matches):
    """Check if value contains any of the provided sub-values"""
    find_all = matches if isinstance(matches, (list)) else [matches]
    for i in find_all:
        if i in value:
            return True
    return False


def init(*args):
    """Initialize filters and globals"""
    env = _TemplateEnvironment(*args)

    # FILTERS
    env.filters["replace_all"] = replace_all
    env.filters["is_defined"] = is_defined
    env.filters["get_type"] = get_type
    env.filters["is_type"] = is_type
    env.filters["is_numeric"] = is_numeric
    env.filters["inflate"] = inflate
    env.filters["deflate"] = deflate
    env.filters["decode_base64_and_inflate"] = decode_base64_and_inflate
    env.filters["deflate_and_base64_encode"] = deflate_and_base64_encode
    env.filters["decode_valetudo_map"] = decode_valetudo_map
    env.filters["urldecode"] = urldecode
    env.filters["strtolist"] = strtolist
    env.filters["listify"] = listify
    env.filters["get_index"] = get_index
    env.filters["grab"] = grab
    env.filters["reach"] = reach
    env.filters["ternary"] = ternary
    env.filters["shuffle"] = shuffle
    env.filters["to_ascii_json"] = to_ascii_json
    env.filters["sortnat"] = sortnat
    env.filters["contains_all"] = contains_all
    env.filters["contains_any"] = contains_any

    # GLOBALS
    env.globals["replace_all"] = replace_all
    env.globals["is_defined"] = is_defined
    env.globals["get_type"] = get_type
    env.globals["is_type"] = is_type
    env.globals["is_numeric"] = is_numeric
    env.globals["inflate"] = inflate
    env.globals["deflate"] = deflate
    env.globals["decode_base64_and_inflate"] = decode_base64_and_inflate
    env.globals["deflate_and_base64_encode"] = deflate_and_base64_encode
    env.globals["decode_valetudo_map"] = decode_valetudo_map
    env.globals["urldecode"] = urldecode
    env.globals["strtolist"] = strtolist
    env.globals["listify"] = listify
    env.globals["get_index"] = get_index
    env.globals["grab"] = grab
    env.globals["reach"] = reach
    env.globals["ternary"] = ternary
    env.globals["shuffle"] = shuffle
    env.globals["to_ascii_json"] = to_ascii_json
    env.globals["sortnat"] = sortnat
    env.globals["contains_all"] = contains_all
    env.globals["contains_any"] = contains_any
    return env


template.TemplateEnvironment = init

# FILTERS
template._NO_HASS_ENV.filters["replace_all"] = replace_all
template._NO_HASS_ENV.filters["is_defined"] = is_defined
template._NO_HASS_ENV.filters["get_type"] = get_type
template._NO_HASS_ENV.filters["is_type"] = is_type
template._NO_HASS_ENV.filters["is_numeric"] = is_numeric
template._NO_HASS_ENV.filters["inflate"] = inflate
template._NO_HASS_ENV.filters["deflate"] = deflate
template._NO_HASS_ENV.filters["decode_base64_and_inflate"] = decode_base64_and_inflate
template._NO_HASS_ENV.filters["deflate_and_base64_encode"] = deflate_and_base64_encode
template._NO_HASS_ENV.filters["decode_valetudo_map"] = decode_valetudo_map
template._NO_HASS_ENV.filters["urldecode"] = urldecode
template._NO_HASS_ENV.filters["strtolist"] = strtolist
template._NO_HASS_ENV.filters["listify"] = listify
template._NO_HASS_ENV.filters["get_index"] = get_index
template._NO_HASS_ENV.filters["grab"] = grab
template._NO_HASS_ENV.filters["reach"] = reach
template._NO_HASS_ENV.filters["ternary"] = ternary
template._NO_HASS_ENV.filters["shuffle"] = shuffle
template._NO_HASS_ENV.filters["to_ascii_json"] = to_ascii_json
template._NO_HASS_ENV.filters["sortnat"] = sortnat
template._NO_HASS_ENV.filters["contains_all"] = contains_all
template._NO_HASS_ENV.filters["contains_any"] = contains_any

# GLOBALS
template._NO_HASS_ENV.globals["replace_all"] = replace_all
template._NO_HASS_ENV.globals["is_defined"] = is_defined
template._NO_HASS_ENV.globals["get_type"] = get_type
template._NO_HASS_ENV.globals["is_type"] = is_type
template._NO_HASS_ENV.globals["is_numeric"] = is_numeric
template._NO_HASS_ENV.globals["inflate"] = inflate
template._NO_HASS_ENV.globals["deflate"] = deflate
template._NO_HASS_ENV.globals["decode_base64_and_inflate"] = decode_base64_and_inflate
template._NO_HASS_ENV.globals["deflate_and_base64_encode"] = deflate_and_base64_encode
template._NO_HASS_ENV.globals["decode_valetudo_map"] = decode_valetudo_map
template._NO_HASS_ENV.globals["urldecode"] = urldecode
template._NO_HASS_ENV.globals["strtolist"] = strtolist
template._NO_HASS_ENV.globals["listify"] = listify
template._NO_HASS_ENV.globals["get_index"] = get_index
template._NO_HASS_ENV.globals["grab"] = grab
template._NO_HASS_ENV.globals["reach"] = reach
template._NO_HASS_ENV.globals["ternary"] = ternary
template._NO_HASS_ENV.globals["shuffle"] = shuffle
template._NO_HASS_ENV.globals["to_ascii_json"] = to_ascii_json
template._NO_HASS_ENV.globals["sortnat"] = sortnat
template._NO_HASS_ENV.globals["contains_all"] = contains_all
template._NO_HASS_ENV.globals["contains_any"] = contains_any

# JINJA
# jinja.filters["replace_all"] = replace_all
# jinja.filters["is_defined"] = is_defined
# jinja.filters["get_type"] = get_type
# jinja.filters["is_type"] = is_type
# jinja.filters["inflate"] = inflate
# jinja.filters["deflate"] = deflate
# jinja.filters["decode_base64_and_inflate"] = decode_base64_and_inflate
# jinja.filters["deflate_and_base64_encode"] = deflate_and_base64_encode
# jinja.filters["decode_valetudo_map"] = decode_valetudo_map
# jinja.filters["urldecode"] = urldecode
# jinja.filters["strtolist"] = strtolist
# jinja.filters["listify"] = listify
# jinja.filters["get_index"] = get_index
# jinja.filters["grab"] = grab
# jinja.filters["reach"] = reach
# jinja.filters["ternary"] = ternary
# jinja.filters["shuffle"] = shuffle
# jinja.filters["to_ascii_json"] = to_ascii_json
# jinja.filters["sortnat"] = sortnat
# jinja.filters["contains_all"] = contains_all
# jinja.filters["contains_any"] = contains_any


async def async_setup(hass, hass_config):
    """Set up this component using YAML."""

    _LOGGER.info('Setting up "' + DOMAIN + '" (' + COMPONENT_TITLE + ')')

    tpl = template.Template("", template._NO_HASS_ENV.hass)

    tpl._env.globals = replace_all
    tpl._env.globals = is_defined
    tpl._env.globals = get_type
    tpl._env.globals = is_type
    tpl._env.globals = is_numeric
    tpl._env.globals = inflate
    tpl._env.globals = deflate
    tpl._env.globals = deflate_and_base64_encode
    tpl._env.globals = decode_base64_and_inflate
    tpl._env.globals = decode_valetudo_map
    tpl._env.globals = urldecode
    tpl._env.globals = strtolist
    tpl._env.globals = listify
    tpl._env.globals = get_index
    tpl._env.globals = grab
    tpl._env.globals = reach
    tpl._env.globals = ternary
    tpl._env.globals = shuffle
    tpl._env.globals = to_ascii_json
    tpl._env.globals = sortnat
    tpl._env.globals = contains_all
    tpl._env.globals = contains_any
    return True


async def async_setup_entry(hass, entry):
    return True


async def async_remove_entry(hass, entry):
    return True
