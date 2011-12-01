'''
Using Widgets
=============

Template Tags
-------------

.. automodule:: widgets.templatetags.widget_tags


AJAX Loading
------------

.. note:: Unstable

Widgets must be frozen (:ref:`freezing`) in the catalogue before they
can be dynamically loaded in production. Loading widgets by class name is
available for users with explict permission only.

The script :file:`/media/widgets/js/widget_tools.js` provides a jQuery plugin
`loadWidget`.

.. js:function:: $.loadWidget(config)

    Where `config` is a JavaScript object with the following properties:

    :param name:
        The name you gave the frozen widget.

    :param data:
        Values to pass to the widget. Only options that haven't been
        frozen in place can be assigned.

    :param success:
        A callback function that takes the returned widget as a
        parameter.

        .. js:class:: Widget

            .. js:attribute:: html

                Rendered widget HTML.

            .. js:attribute:: js_media

                A list of JavaScript media URLs.

            .. js:attribute:: css_media

                A list of CSS media URLs.

            .. js:attribute:: rendered_media

                Rendered CSS and JavaScript tags.

            .. js:attribute:: addMedia

                A method to add this widget's media to the current
                page, if it hasn't already been added.

    :param error:
        A callback function called on the event of a request error.

    :param url:
        This defaults to the loading frozen widgets, but can be customised
        to load by class name in admin mode.

.. js:function:: $.fn.loadWidget(config)

    As above, but automatically loads the widget into the element and inserts
    media. Triggers **widgetsReady** after load.


.. note::

    When AJAX loading, Javascript files are loaded before the widget body is
    placed in the DOM. Therefore, after a widget has been placed in the DOM,
    the **widgetsReady** event must be triggered on the document object for
    script that requires the widget present. :js:func:`$.fn.loadWidget` will do
    this automatically.

    Javascript code that requires a widget to be present should do the
    following::

        $(document).bind("ready widgetsReady", function () { ... });


.. _freezing:

Freezing Widgets
----------------

The widget catalogue can be accessed on the admin site. Here you can save
widgets with a name and some 'frozen' options. Users will only be able to
change options that have not been checked as frozen.

Only frozen widgets can be dynamically loaded by all users. AJAX loading by
class name is only available to users with explicit permission due to
the security vulnerabilities involved.


Creating a Widget
=================

Widget classes can be defined anywhere, but should derive from
:py:class:`WidgetBase`.

Widgets can be customised by overriding methods and defining class
attributes.


Overridable methods
-------------------

.. automethod:: widgets.base.WidgetBase.render
.. automethod:: widgets.base.WidgetBase.as_csv
.. automethod:: widgets.base.WidgetBase.as_png
.. automethod:: widgets.base.WidgetBase.as_svg

Customisable class attributes
-----------------------------

.. py:attribute:: WidgetBase.options

    This is a list of objects deriving from :py:class:`options.Option` that
    define the arguments given to the widget. Widgets can be passed values
    through the `widget` template tag, by GET requests, or by values 'frozen'
    by the widget catalogue (:ref:`freezing`).

    Widget forms are generated from the options defined here. These forms are
    used in the widget catalogue.

.. py:attribute:: WidgetBase.media

    A property defined using Django's :py:class:`Media` class.
    See https://docs.djangoproject.com/en/1.2/topics/forms/media/

    By default it builds a :py:class:`Media` object using the attributes
    :py:attr:`WidgetBase.css_media` and :py:attr:`WidgetBase.js_media`, which
    are a list of filenames.


Helpers
-------

.. automethod:: widgets.base.WidgetBase.render_to_response


Conventions
-----------

* Widget templates should have the python class name as a CSS class and the
  widget UID as the html ID of the top level element. The
  :py:meth:WidgetBase.render_to_response method will do this for you
  automatically.

* All CSS should have the python class name in the selector.


Example
-------
::

    from widgets.base import WidgetBase
    from widgets.options import BoolOption

    class ExampleWidget(WidgetBase):
        options = [
            BoolOption('example', '-e'),
            ]

        js_media = ['path/to/some.css']
        css_media = ['path/to/some.js']

        def render(options, context):
            return self.render_to_response('path/to/template', context)


Internal API documentation
==========================

Options
-------

.. automodule:: widgets.options
   :members:
'''
__version__ = '1.0.0'
