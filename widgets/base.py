'''Fundamental classes and functions for widgets.'''

import hashlib
import sys
from copy import copy
from StringIO import StringIO
import subprocess

from django.template import Template, Context
from django.template.loader import render_to_string
from django.forms import Media
from django.utils.safestring import mark_safe
from django.conf import settings


class ClassProperty(property):
    """So we can use a classmethod as a property.

    See:
    http://stackoverflow.com/questions/128573/using-property-on-classmethods

    """
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class WidgetBase(object):
    '''Base class for all widgets.'''

    options = []
    example = {}

    css_media = []
    js_media = []

    abstract = True

    @ClassProperty
    @classmethod
    def is_abstract(cls):
        return 'abstract' in cls.__dict__

    @ClassProperty
    @classmethod
    def description(cls):
        return cls.__doc__

    @classmethod
    def classname(cls):
        '''
        Return the class name. Double underscore members cannot be called from
        templates, but we want to expose this for convenience.

        '''
        return str(cls.__name__)

    @classmethod
    def qualified_classname(cls):
        '''Helper method to return the class name with module prepended.'''
        return "%s.%s" % (cls.__module__, cls.__name__)

    @property
    def media(self):
        '''
        The media property, using django's :py:class:`Media` class.

        This will be overriden in subclasses, and extra functionality such as
        adding in other media (e.g. for maps) would be done here.

        By default, uses js_media and css_media attributes on the class to
        build a :py:class:`Media` object.

        '''
        return Media(
            css={'all': self.css_media},
            js=self.js_media)

    def generate_uid(self, options):
        '''A uid for a widget that should be unique per page.'''
        uid = hashlib.md5()
        for item in sorted(options.items()):
            uid.update(str(item))
        uid.update(self.__class__.__name__)
        return "generated_%s" % uid.hexdigest()

    def _render_wrapper(self, options, context, **kwargs):
        '''
        Internal render method. Push new scope and add widget-specific
        context.

        '''
        saved_context_dicts = copy(context.dicts)
        context.push()

        # default uid can be overridden in kwargs
        context['uid'] = self.generate_uid(options)
        context['classname'] = self.__class__.__name__
        context['options'] = options
        context['qualified_classname'] = self.qualified_classname()
        if 'widget_debug' in context and context['widget_debug']:
            import inspect
            from widgets.utils import (
                options_to_tag_string, options_to_query_string)
            context['css'] = self.media._css
            context['js'] = self.media._js
            context['query_string'] = options_to_query_string(
                self.__class__,
                options)
            context['tag_string'] = options_to_tag_string(
                self.__class__,
                options)
            context['widget_file'] = inspect.getsourcefile(self.__class__)
        context.update(kwargs)
        rendered_widget = self.render(options, context)

        # Pop back context scope to state before widget render.  We can't rely
        # on a single 'Context.pop' because 'Context.update' also pushes a new
        # scope.
        context.dicts = saved_context_dicts

        return mark_safe(rendered_widget)

    def render(self, options, context):
        '''
        This method should return a string that will replace the template tag
        or be returned as a `html` value for an AJAX loaded widget.  The helper
        method :py:meth:`.render_to_response` should be
        used to render templates. By default it returns an empty string.

        '''
        return ""

    def render_to_response(self, template, context):
        '''
        Render a widget template. Surrounds the rendered HTML with a div. The
        div has a unique id generated from the widget's options and a class
        attribute with the widget's Python class.

        '''
        context['widget_instance'] = self
        if isinstance(template, Template):
            context['rendered_widget'] = template.render(context)
            context['widget_template'] = 'DYNAMIC'
        else:
            context['rendered_widget'] = render_to_string(template, context)
            context['widget_template'] = template
        return render_to_string(
            getattr(
                settings,
                'WIDGET_WRAPPER_TEMPLATE',
                'widgets/wrapper.html'),
            context)

    def downloadable_as(self):
        """Which types have been implemented?"""
        avail = {
            'csv': 'CSV',
            'svg': 'SVG',
            'png': 'PNG',
            'html': 'HTML',
        }
        enabled = {}
        for _as in avail.keys():
            try:
                getattr(self, 'as_%s' % _as)({}, None, {})
            except NotImplementedError:
                continue
            except:  # any others are expected as we didn't give opts etc
                pass
            enabled[_as] = avail[_as]
        if len(enabled.keys()) == 0:
            return None

        return enabled

    def as_html(self, options, fp):
        """Just render it and spit it out."""
        context = Context({
            'options': options,
        })
        fp.write(self.render(options, context))

    def as_csv(self, options, fp, headers=False, *args):
        """
        Extract widget data as CSV, writing it to the file-type object
        specified by `fp`.

        By default, this should output a row of data corresponding to the
        data used to render the widget.  Pass `headers=True` to extract a set
        of CSV headers instead of the data.

        """
        raise NotImplementedError

    def as_svg(self, options, fp, render_options={}):
        """
        Render a widget in SVG format to the file-type object specified by
        `fp`.

        Pass extra SVG-specific options to the renderer using the
        `render_options` argument.

        """
        raise NotImplementedError

    def as_png(self, options, fp, render_options={}):
        """
        Render a widget in PNG format to the file-type object specified by
        `fp`.

        Pass extra PNG-specific options to the renderer using the
        `render_options` argument.

        The default implementation will call as_svg and attempt to convert
        the output to PNG using ImageMagick.

        """
        # try to generate an SVG and then convert to PNG
        svg_fp = StringIO()
        self.as_svg(options, svg_fp, render_options)
        svg_fp.seek(0)
        p = subprocess.Popen(['convert','-background','none','svg:-','png:-'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        out,err = p.communicate(svg_fp.read())
        if p.wait():
            raise RuntimeError("Failed to convert to SVG\n%s" % err)
        fp.write(out)

    def as_design(self, options, *args):
        """
        Extract widget data as a list, suitable for adding to a CSV file
        for sending to design to include in a printed scorecard.

        """
        return []


def get_widget_class(name):
    '''
    Load the widget class provided.
    :param name: a fully qualified python class name.
    '''
    # load the widget class
    path = name.split('.')
    module_name = ".".join(path[:-1])
    class_name = path[-1]

    # import the module if needed
    if module_name not in sys.modules:
        __import__(module_name)
    module = sys.modules[module_name]

    # find the class and check it is a widget
    assert class_name in module.__dict__, \
        "Widget '%s' not found in module: %s" % (name, module.__name__)
    widget_class = module.__dict__[class_name]
    assert issubclass(widget_class, WidgetBase), \
        "%s does not inherit from WidgetBase" % name

    return widget_class
