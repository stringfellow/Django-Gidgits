'''
Lexing & Parsing command-style strings.
This is used in parsing widget template tags such as::

    {% widget <name> --arg1 "literal string" --arg2 variable %}
'''

import re


class OptionParserError(Exception):
    pass


class OptionLexer(object):
    '''Parses an argument string into tokens and expands options.'''

    def __init__(self, arguments):
        # If we are given a string, split it
        if isinstance(arguments, basestring):
            arguments = re.split("( |\\\".*?\\\"|'.*?')", arguments.strip())

        # Assume we have a list of strings here
        assert hasattr(arguments, '__iter__')

        self._iterator = self._expanded(arguments)
        self.exhausted = False
        self.token = None

    def _expanded(self, tokens):
        '''
        Expands options with multiple flags (e.g. -abc => -a -b -c) and
        discards whitespace.

        '''
        for token in tokens:
            if token.startswith('-') and not token.startswith('--'):
                for flag in token[1:]:
                    yield "-%s" % flag
            elif len(token.strip()) > 0:
                yield token

    @property
    def token_is_option(self):
        '''Is the current token an option?'''
        return self.token.startswith("-")

    def consume(self):
        '''Drop the current token, and store the next in :py:attr:`token`.'''
        try:
            self.token = self._iterator.next()
        except StopIteration:
            self.exhausted = True

    def __iter__(self):
        return self._iterator


def _find_option(option_list, arg):
    '''Find an option by form or long_form, or raise an error'''
    for opt in option_list:
        if opt.short_form == arg or opt.long_form == arg:
            return opt
    raise OptionParserError("Unknown argument: %s" % arg)


def parse_argument_list(option_list, arguments):
    '''
    Parse a string using `option_list`.

    :param option_list: A list of :py:class:`Option` objects.
    :param arguments: A string representing values.
    :returns: List of (option, value)

    '''
    values = []
    lexer = OptionLexer(arguments)

    # Get first token
    lexer.consume()

    while not lexer.exhausted:
        opt = _find_option(option_list, lexer.token)
        lexer.consume()
        values.append((opt, opt.parse_tokens(lexer)))

    return values
