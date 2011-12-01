#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""The widget registry.

A lot like admin, this contains a Register class (like AdminSite) that loads
and stores the registered widgets, after checking they are 'valid' (i.e. that
they subclass WidgetBase). This means each app can have their own set of
widgets (or gidgits, or whatever other ridiculous name the software team can
agree on that doesn't conflict with a namespace), and these will automatically
be loaded etc on init.

"""
import os
import pkgutil
import inspect
import logging

from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict

from widgets.base import WidgetBase, get_widget_class

log = logging.getLogger(__name__)

class Registry(object):
    """A class for registering widgets to.

    This should be used to prevent random code-loading and for pre-load
    importing.

    """

    def __init__(self):
        self._register = {}

    def register_by_qualified_name(self, name):
        """Add the widget by name, if it isn't already there."""
        if name in self._register:
            return
        self._register[name] = get_widget_class(name)

    def _add_classes(self, app_name, widget_noun, modnm=None):
        """Add the module's classes to the registry."""
        if modnm in ('options',):  # don't import
            return
        widget_path = ".".join([app_name, widget_noun])
        if modnm:  # if the widgets is a 'package' then there'll be modnm too
            widget_path = widget_path + "." + modnm
        widget_module = import_module(widget_path)
        for name, obj in inspect.getmembers(widget_module):
            if (inspect.isclass(obj) and  # check it's a class
                obj.__module__ == widget_path and  # and from this module
                issubclass(obj, WidgetBase)):  # and subclasses WidgetBase
                # the name as it appears in the import tag:
                fully_qualified_widget = ".".join([widget_path, name])
                # add it to the registry
                self._register.setdefault(fully_qualified_widget, obj)

    def register(self, app_name, widget_noun='widgets'):
        """Try and add this app's widgets to the registry."""
        package = __import__(app_name)
        for _, modnm1, ispkg1 in pkgutil.iter_modules(package.__path__):
            if modnm1 == widget_noun:  # see if the widgets module exists
                if ispkg1:  # if it is a package, then descend in...
                    for _, modnm2, ispkg2 in pkgutil.iter_modules([
                    os.path.join(package.__path__[0], widget_noun)]):
                        self._add_classes(app_name, widget_noun, modnm2)
                else:  # its just a widgets.py file.
                    self._add_classes(app_name, widget_noun)

    def register_main(self, app_name):
        """Try and add this app's widgets to the registry."""
        package = __import__(app_name)
        for _, modnm1, ispkg1 in pkgutil.iter_modules(package.__path__):
            self._add_classes(app_name, modnm1)

    def widgets_by_app(self):
        """Return an app->[widgets] dict."""
        apps = {}
        for cls, widget in self._register.items():
            app = cls.split('.')[0]
            apps.setdefault(app, []).append(widget)
        return apps

    def find(self, classname):
        """Return a registered widget or register and return by classname."""
        if classname in self._register:
            return self._register[classname]
        else:
            self.register_by_qualified_name(classname)
            assert classname in self._register
            return self._register[classname]


# This global object will hold all registered widgets.
registry = Registry()


def autodiscover(widget_noun='widgets'):
    """Like admin's autodiscover.

    Are these widgets, gadgets, gizmos, gidgits, wadgets...?
    Just specify the noun you want, really.

    """
    import copy
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's widgets module.
        try:
            before_import_register = copy.copy(registry._register)
            registry.register(app, widget_noun)
        except Exception, e:
            log.error(e)
            registry._register = before_import_register

            # Decide whether to bubble up this error. If the app just
            # doesn't have a widgets module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, widget_noun):
                raise e

    # autodiscover main gidgits directory
    try:
        mod = import_module(widget_noun)
        before_import_register = copy.copy(registry._register)
        registry.register_main(widget_noun)
    except Exception, e:
        log.error(e)
        registry._register = before_import_register
