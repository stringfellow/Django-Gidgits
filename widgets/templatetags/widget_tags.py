'''
Inside a template, after loading widget_tags, you can use the `widget` tag::

    {% widget [class] --arg1 variable --arg2 "literal string" %}

The first argument is the fully qualified class name and the remaining
arguments are command-line style arguments. Note that values are interpreted
as template variables, so strings must be quoted.

.. autofunction:: widgets.template.render_to_response

Example template::

    {% load widget_tags %}
    <html>
        <head>
            {% include "widgets/head.html" %}
        </head>
        <body>
            {% widget example.WidgetClass1 --arg "value1" %}
            {% widget example.WidgetClass2 --arg "value2" %}
        </body>
        <script>
            {{ widgets.script }}
            $(function () {
                {{ widgets.init_script }}
            });
        </script>
    </html>
'''

import re

from django import template
from django.template.defaultfilters import stringfilter
from django.template.loader import get_template

from widgets.options import process_values
from widgets.registry import registry as widget_registry
from widgets.command_parser import parse_argument_list

register = template.Library()


# For friendly failure, consider subclassing this node and catching exceptions
# in the appropriate methods. The tag could be called 'safe_widget'. The node
# class below should throw exceptions on failure. See revision 24864 for
# removed silent failures. 'safe_widget' could also check permissions, but this
# shouldn't be necessary by default as views should have already checked.

class WidgetRenderNode(template.Node):

    def __init__(self, classname, arguments, as_name=None):
        widget_class = widget_registry.find(classname)
        self.as_name = as_name
        self.widget = widget_class()
        self.values = parse_argument_list(widget_class.options, arguments)

    @property
    def media(self):
        return self.widget.media

    def render(self, context):
        from widgets.utils import options_to_query_string
        resolved = dict((opt.name, opt.resolve_value(context, value))
                        for opt, value in self.values)
        options = process_values(resolved, self.widget.options)

        as_name = self.as_name
        if as_name:
            as_name = self.as_name.resolve(context)
        return self.widget._render_wrapper(
            options=options,
            context=context,
            uid=as_name,
            raw_options=resolved,
            query_string=options_to_query_string(
                self.widget.__class__,
                options))

    def render_head(self):
        return self.widget.render_head()


def widget_render_tag(parser, token):
    args = token.split_contents()

    # Check syntax
    if not ((len(args) >= 2) and (args[0] == 'widget')):
        raise template.TemplateSyntaxError(
            "Syntax: {%% widget class [arguments...] [as 'some_uid'] %%} "
            "Received: {%% %s %%}" % token.contents)

    # Parse 'as' option
    if "as" == args[-2]:
        as_name = template.Variable(args[-1])
        args = args[:-2]
    else:
        as_name = None

    return WidgetRenderNode(args[1], args[2:], as_name)

register.tag('widget', widget_render_tag)


def _is_literal_string(value):
    return value.startswith('"') or value.startswith("'")


class BoxedWidget(WidgetRenderNode):

    def __init__(self, template_, title, classname, arguments, as_name=None):
        self.template = template_
        if not _is_literal_string(self.template):
            self.template = template.Variable(template_)
        self.title = title[1:-1]
        super(BoxedWidget, self).__init__(classname, arguments, as_name)

    def render(self, context):
        rendered_widget = super(BoxedWidget, self).render(context)
        if type(self.template) == basestring:
            template_ = get_template(self.template)
        else:
            template_ = get_template(self.template.resolve(context))

        context.update({
            'box_widget': rendered_widget,
            'box_title': self.title,
            'widget': self.widget,

            # temp(?) hack
            'uid': self.as_name.resolve(context),
        })

        return template_.render(context)


def box_widget_render_tag(parser, token):
    args = token.split_contents()

    # Check syntax
    if not ((len(args) >= 4) and (args[0] == 'box_widget')):
        raise template.TemplateSyntaxError(
            "Syntax: {%% box_widget template title class [arguments...] %%} "
            "Received: {%% %s %%}" % token.contents)

    if "as" == args[-2]:
        as_name = template.Variable(args[-1])
        args = args[:-2]
    else:
        as_name = None

    return BoxedWidget(args[1], args[2], args[3], args[4:], as_name=as_name)

register.tag('box_widget', box_widget_render_tag)


# Should be moved to utils_tags or similar
@register.filter
@stringfilter
def decamel(value):
    return re.sub(r"([A-Z]{1})", r" \1", value)
