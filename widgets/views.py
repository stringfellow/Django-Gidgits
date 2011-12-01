#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
import datetime

from django.template import RequestContext
from django.http import HttpResponse

from widgets.template import render_to_response
from widgets.options import process_values, BoolOption
from widgets.base import get_widget_class

def direct_to_template(request, template, extra_context=None, **kwargs):
    """
    Render a given template with any extra URL parameters in the context as
    ``{{ params }}``, using the widget response
    """
    if extra_context is None: extra_context = {}
    dictionary = {'params': kwargs}
    for key, value in extra_context.items():
        if callable(value):
            dictionary[key] = value()
        else:
            dictionary[key] = value
    
    c = RequestContext(request, dictionary)
    return render_to_response(template, context_instance=c, **kwargs)


def _getquery_to_dict(options, values, drop_unfrozen=False):
    '''Translate a GET into widget values. Remove non-used options.'''

    def _valid_option(opt):
        """Various things make an option valid in the context.

        Most problems come from catalogue where we present all values but
        can turn them on or off. Other places like style page etc. use just
        the options they need. Check for 'catalogue' and proceed accordingly.

        """
        use_key = "use:%s" % opt.name
        return (
            not 'catalogue' in values or
            (use_key in values and values[use_key] == 'on') or
            opt.required or
            isinstance(opt, BoolOption)
        )

    value_dict = dict(
        (opt.name, opt.get_value_from_query(values))
        for opt in options
        if _valid_option(opt)
    )

    value_dict.update(dict(
        (opt.name, opt.default)
        for opt in options
        if not _valid_option(opt) and opt.default)
    )
    return value_dict


def widget_download_response(request, classname):
    """Retrieve a widget as a different format."""
    method = request.GET.get("as", "svg")
    mimetype = {
        'svg': "image/svg+xml",
        'png': "image/png",
        'csv': "text/csv",
        'html': "text/html",
    }[method]

    widget_class = get_widget_class(classname)
    widget = widget_class()

    fn = getattr(widget, 'as_%s' % method)

    values = _getquery_to_dict(widget_class.options, request.GET)
    values = process_values(values, widget_class.options)

    response = HttpResponse(mimetype=mimetype)
    response['Content-Disposition'] = 'attachment; filename=%s_%s.%s' % (
        classname,
        datetime.datetime.now(),
        method)
    try:
        fn(values, response)
        return response
    except NotImplementedError:
        return HttpResponse("Sorry that format is not available.", status=404)
