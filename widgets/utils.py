'''Various widget related utilities.'''
import urllib
from django.utils.html import escape


def options_to_command_string(widget_class, options, short=False):
    '''
    Reverse the options and return a command line string.
    i.e. the inverse of parse_command_string.

    '''
    arguments = []
    for opt in widget_class.options:
        if opt.name in options:
            arguments.append(short and opt.form or opt.long_form)
            if opt.takes_argument:
                arguments.append("'%s'" % options[opt.name])

    widget_name = "%s.%s" % (widget_class.__module__, widget_class.__name__)
    arg_string = " ".join(arguments)
    return "%s %s" % (widget_name, arg_string)


def options_to_tag_string(widget_class, options):
    """
    Render the options part of a widget tag.
    Excludes widget class.

    """
    arguments = {}
    for opt in widget_class.options:
        if opt.name in options:
            arg = opt.get_raw_value(options[opt.name])
            if type(arg) == list and arg:
                arguments[opt] = '%s' % " ".join(
                    ['"%s"' % escape(v) for v in arg])
            elif type(arg) != bool and arg:
                arguments[opt] = '"%s"' % escape(str(arg))
            else:
                # only render the arg name if this is bool
                if arg:
                    arguments[opt] = ""

    query_string = ' '.join(
        ['%s %s' % (k.long_form, v)
         for (k, v) in arguments.items()])
    return query_string


def options_to_query_string(widget_class, options):
    """
    Render the options part of a query string.
    Excludes widget class.

    """
    arguments = {}
    list_args = {}
    for opt in widget_class.options:
        if opt.name in options:
            arg = opt.get_raw_value(options[opt.name])
            if type(arg) != bool and arg:
                if not isinstance(arg, list):
                    arguments[opt.name] = arg
                else:
                    list_args[opt.name] = arg
            else:
                # only render the arg name if this is bool
                if arg:
                    arguments[opt.name] = ""

    query_string = '&'.join(
        ['%s=%s' % (k, urllib.quote(str(v)))
         for (k, v) in arguments.items()])
    query_string = "%s&%s" % (query_string, "&".join(
        ['%s=%s' % (k, urllib.quote(str(v)))
         for k, vals in list_args.items()
         for v in vals
        ]))

    return query_string


def widget_render_cache_key(widget, options, context):
    '''Key to use for rendering cache.'''
    return widget.generate_uid(options)
