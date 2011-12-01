from functools import wraps

from django.template import RequestContext

from widgets.template import render_to_response
from widgets.base import WidgetBase


def render_to(template=None, media=None):
    """Equivalent of django-annoying's :func:`render_to`."""
    def renderer(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            output = function(request, *args, **kwargs)
            if not isinstance(output, dict):
                return output
            tmpl = output.pop('TEMPLATE', template)
            return render_to_response(
                tmpl, output,
                context_instance=RequestContext(request),
                media=media)
        return wrapper
    return renderer


class PermissionDeniedWidget(WidgetBase):
    def __init__(self, uid, original_classname):
        self.uid = uid
        self.original_classname = original_classname

    def render(self, options, context):
        context.update({
            'options': options,
            'original_classname': self.original_classname,
        })

        return self.render_to_response(
            "widgets/base/PermissionDeniedWidget.html",
            context
        )


def render_or_deny(fn):
    """
    Common decorator to wrap render that calls obj.access_check first.
    if not accessible, return Perm. Denied. widget render.

    """
    @wraps(fn)
    def _wrapped(obj, options, context, *args, **kwargs):
        if not obj.access_check(options, context['request'].user):
            return PermissionDeniedWidget(
                obj.uid,
                obj.classname()
            ).render(options, context)
        else:
            return fn(obj, options, context)
    return _wrapped
