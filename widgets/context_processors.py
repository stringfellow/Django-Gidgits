#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
from django.conf import settings


def debug(request):
    return {'widget_debug': getattr(settings, 'WIDGET_DEBUG', False)}
