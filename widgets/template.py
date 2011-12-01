from django.http import HttpResponse
from django.template import loader, Context, loader_tags, defaulttags, Template
from django.forms import Media

from widgets.templatetags.widget_tags import WidgetRenderNode


def _find_widget_nodes(nodelist):
    '''Traverse the nodes of a template and extract all widgets.'''

    # This will recursively decend through the nodes to find any
    # widgets. This includes the body of an 'extends' tag.
    widgets = list(nodelist.get_nodes_by_type(WidgetRenderNode))

    # Traverse up through 'extends' tags.
    for ext in nodelist.get_nodes_by_type(loader_tags.ExtendsNode):
        # note that we can only traverse non-variable 'extends' as we do not
        # have a context.
        if ext.parent_name:
            tpl = loader.get_template(ext.parent_name)
            widgets.extend(_find_widget_nodes(tpl.nodelist))

    # Traverse down through (constant) 'include' tags
    for inc in nodelist.get_nodes_by_type(loader_tags.ConstantIncludeNode):
        widgets.extend(_find_widget_nodes(inc.template.nodelist))

    return widgets


def render_to_response(template_path, context={}, context_instance=None,
                       variable_templates=None, media=None):
    '''
    A replacement for Django's render_to_response that provides some extra
    context:

    **{{ widgets.media }}**
        A widget media object for all widgets contained in the template, with
        duplicates removed.

    :param variable_templates: A list of known `include` template names that
        occur in this template - we can't inspect them in the template before
        render time and we need to be able to walk their node tree so we have
        to do this little bit of extra work here. Example::

            {% with "widgets/test_inclusion.html" as some_template %}
            {% include some_template %}
            {% endwith %}

        will require you to pass in ``["widgets/test_inclusion.html"]``.

    :param media: A Django Media object to add widget media to. By default
        uses a new :class:`Media` object.

    '''
    
    if isinstance(template_path, (list, tuple)):
        template = loader.select_template(template_path)
    else:
        template = loader.get_template(template_path)
    variable_templates = variable_templates or []

    # convert template names to template objects for node-checking.
    variable_templates_ = [
        loader.get_template(tpl)
        for tpl in variable_templates]

    widget_template = WidgetTemplateWrapper(
        template=template,
        variable_includes=variable_templates_,
        media=media)

    ctxt = context_instance or Context()
    ctxt.update(context)
    return HttpResponse(widget_template.render(ctxt))


class WidgetTemplateWrapper(object):
    '''Wrapper for templates containing widgets.'''

    def __init__(self, template, variable_includes=None, media=None):
        """Setup and get all the widgets from template.

        Note, we may be passed variable_includes here because IncludeNodes use
        a context variable that can't be resolved until render time. We need
        to know all the widget nodes up-front so must be handed the extra
        templates as well. This will be passed in to render_to_response.

        """
        variable_includes_ = variable_includes or []

        self.template = template
        self.widget_nodes = _find_widget_nodes(template.nodelist)
        for template_ in variable_includes_:
            self.widget_nodes.extend(_find_widget_nodes(template_.nodelist))

        self.media = media or Media()
        for node in self.widget_nodes:
            self.media.add_css(node.media._css)
            self.media.add_js(node.media._js)

    def render(self, context):
        '''Returns a string of the rendered template.'''
        context['widgets'] = {
            'media': self.media,
            }
        return self.template.render(context)
