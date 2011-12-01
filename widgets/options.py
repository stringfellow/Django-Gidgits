'''Options for use in the :py:attr:`options` property of widgets.'''
import logging

from django.db import models
from django.forms import CheckboxInput, TextInput
from django.template import Variable

from widgets.command_parser import OptionParserError
from django.forms import SelectMultiple, Select


class OptionError(Exception):
    pass


class Values(dict):
    '''Class to expose dict values as attrs for convenience.'''

    def __getattr__(self, name):
        return self[name]


def process_values(values, options):
    '''
    Given a dictionary of values, check required options are present and filter
    the options according to their class.

    :param values: Dictionary of values.
    :param options: List of :py:class:`Option`.
    :returns: Dictionary of processed values.
    '''
    # Check for required options
    required = set(option.name for option in options if option.required)
    missing = required - set(values.keys())

    if len(missing) > 0:
        raise OptionError("Missing arguments: %s" % missing)

    # Check arguments
    names = set(option.name for option in options)
    unknown = set(values.keys()) - names

    if len(unknown) > 0:
        raise OptionError("Unknown arguments: %s" % unknown)

    # Return filtered options
    logging.debug(values)
    logging.debug(options)
    return Values((opt.name, opt.filter(values.get(opt.name, opt.default)))
                  for opt in options)


class Option(object):
    '''
    Default option that takes one parameter. Displays in forms as a text field.

    :param name: Key to be used in the value dictionary, label for forms, and
        form input name.
    :param short_form: Short form of option, usually beginning with one hyphen.
    :param long_form: Long form of option, by default the name prefixed with
        two hyphens.
    :param default: Default value.
    :param required: Require the presence of this option. Default true.
    :param help: Help string for this option.

    '''

    @property
    def classname(self):
        """Used in templates etc where __class__ not allowed."""
        return str(self.__class__.__name__)

    def __init__(self, name, short_form=None, long_form=None,
                 default=None, required=True, help=None):
        self.name = name
        self.short_form = short_form
        self.long_form = long_form or ("--%s" % name.replace('_', '-'))
        self.help = help
        self.default = default
        self.required = required

    def __repr__(self):
        return "%s:%s" % (self.__class__.__name__, self.name)

    def form_field(self, value):
        '''
        Return rendered HTML for forms. The form element should use the option
        name as its `name` attribute.

        :param value: Initial value.
        :returns: Form HTML.
        '''
        return TextInput().render(self.name, value)

    def _get_var(self, lexer):
        '''Parse a :py:class:`Variable`.'''
        if lexer.token_is_option:
            raise OptionParserError('Unexpected option: %s', lexer.token)
        value = lexer.token
        lexer.consume()
        return Variable(value)

    def parse_tokens(self, lexer):
        '''
        Parse the value of this option from a string input.

        :returns: Unresolved option value.
        '''
        return self._get_var(lexer)

    def resolve_value(self, context, value):
        '''Resolve this option's value against a template context.'''
        return value.resolve(context)

    def filter(self, value):
        '''Filter a resolved value. Identity by default.'''
        return value

    def get_value_from_query(self, query):
        '''Return value from :py:class:`QueryDict`.'''
        return query.get(self.name, self.default)

    def get_raw_value(self, value):
        """Return the value as it was on input."""
        return value


class BoolOption(Option):
    '''
    An option that evaluates to True when present in the command string.
    Displays in forms as a checkbox.

    '''
    def __init__(self, *args, **kwargs):
        super(BoolOption, self).__init__(*args, **kwargs)
        self.required = False
        self.default = False

    def form_field(self, value):
        return CheckboxInput().render(self.name, value)

    def parse_tokens(self, lexer):
        return True

    def resolve_value(self, context, value):
        return value

    def get_value_from_query(self, query):
        return self.name in query


class SelectOption(Option):
    '''
    An option restricted to a list of choices.
    Displays in forms as a dropdown.

    '''
    def __init__(self, choices, *args, **kwargs):
        super(SelectOption, self).__init__(*args, **kwargs)
        self.choices = choices

    def form_field(self, value):
        choices = self.choices() if callable(self.choices) else self.choices
        return Select().render(self.name, value, choices=choices)


class MultiOption(Option):
    '''
    An option that takes multiple arguments.
    Displays in forms as a multiple select widget.

    '''
    def __init__(self, choices, *args, **kwargs):
        kwargs['default'] = kwargs.get('default', [])
        kwargs['required'] = kwargs.get('required', False)
        super(MultiOption, self).__init__(*args, **kwargs)
        self.choices = choices

    def form_field(self, value):
        choices = self.choices() if callable(self.choices) else self.choices
        return SelectMultiple().render(self.name, value, choices=choices)

    def parse_tokens(self, lexer):
        value = []
        while not lexer.token_is_option and not lexer.exhausted:
            value.append(self._get_var(lexer))
        return value

    def resolve_value(self, context, value):
        return [item.resolve(context) for item in value]

    def get_value_from_query(self, query):
        return query.getlist(self.name)

    def get_raw_value(self, value):
        if value:
            vals = [
                (isinstance(val, models.Model) and getattr(val, self.key) or
                 val) for val in value]
            return vals
        return value


class ListOption(MultiOption):
    """Allow for non-model undefined lists of things (strings)."""

    def __init__(self, *args, **kwargs):
        super(ListOption, self).__init__(None, *args, **kwargs)

    def form_field(self, value):
        return TextInput(attrs={
            'class': 'ListOption',
        }).render(self.name, " ".join(value))

    def get_value_from_query(self, query):
        """Get the value, but know that it is a space-delimeted string.
        
        Passing an empty string here results in a single blank item list.
        Undesirable, and I'm sure this should be better handled. ~spike
        """
        try:
            value = query.getlist(self.name)
        except Exception, e:
            logging.debug("Couldn't getlist from query: %s" % self.name)
            value = self.default
        return value


class _QueryOptionMixin(object):
    def get_choices(self):
        if self._fields:
            return self._query.values_list(*self._fields)
        return [(i.pk, i.__unicode__()) for i in self._query]

    @property
    def key(self):
        if self._fields:
            return self._fields[0]
        return 'pk'


class ForeignKeyOption(SelectOption, _QueryOptionMixin):
    '''Option that takes a foreign key as an argument.'''

    def __init__(self, *args, **kwargs):
        self._query = kwargs.pop("query")
        self._fields = kwargs.pop("fields", None)
        super(ForeignKeyOption, self).__init__(
            self.get_choices, *args, **kwargs)

    def filter(self, value):
        if isinstance(value, models.Model):
            return value
        if value:
            return self._query.get(**{self.key: value})

    def get_raw_value(self, value):
        if isinstance(value, models.Model):
            return getattr(value, self.key)
        else:
            return value


class MultiForeignKeyOption(MultiOption, _QueryOptionMixin):
    '''Option that takes many foreign keys its arguments.'''

    def __init__(self, *args, **kwargs):
        self._query = kwargs.pop("query")
        self._fields = kwargs.pop("fields", None)
        super(MultiForeignKeyOption, self).__init__(
            self.get_choices, *args, **kwargs)

    def filter(self, value):
        if isinstance(value, models.Model):
            return value
        if value:
            key = "%s__in" % self.key
            return self._query.filter(**{key: value})
