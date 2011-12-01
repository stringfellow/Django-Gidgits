from lxml import etree

from unittest import TestCase, main

from django.template import Context, Template
from django.template.loader import get_template
from django.test.utils import setup_test_environment
from django.conf import settings

from widgets.command_parser import OptionLexer, OptionParserError
from widgets.base import WidgetBase
from widgets.options import Option
from widgets.template import WidgetTemplateWrapper


class LexerTests(TestCase):
    def assert_lex(self, arguments, tokens):
        lexer = OptionLexer(arguments)
        self.assertEqual(tokens, list(lexer))

    def test_simple_lex(self):
        self.assert_lex("a", ["a"])
        self.assert_lex("a b c", ["a", "b", "c"])
        self.assert_lex("  one   two  ", ["one", "two"])

    def test_expand(self):
        self.assert_lex('-a', ['-a'])
        self.assert_lex('-abc', ['-a', '-b', '-c'])
        self.assert_lex('--xyz -abc', ['--xyz', '-a', '-b', '-c'])

    def test_quotes(self):
        self.assert_lex('"a"', ['"a"'])
        self.assert_lex('a "b c" d', ['a', '"b c"', 'd'])

    def test_consume(self):
        lexer = OptionLexer('--a 1 --b 2')
        self.assertEqual(None, lexer.token)
        self.assertFalse(lexer.exhausted)
        lexer.consume()
        self.assertEqual('--a', lexer.token)
        self.assertTrue(lexer.token_is_option)
        lexer.consume()
        self.assertEqual('1', lexer.token)
        lexer.consume()
        self.assertEqual('--b', lexer.token)
        lexer.consume()
        self.assertEqual('2', lexer.token)
        self.assertFalse(lexer.exhausted)
        lexer.consume()
        self.assertTrue(lexer.exhausted)


class OptionTests(TestCase):
    '''Test each Option class.'''
    pass  # TODO


class TestWidget1(WidgetBase):
    def render(self, options, context):
        return "test"


class TestWidget2(WidgetBase):
    options = [
        Option('testing', '-t', default="xxx"),
        ]

    def render(self, options, context):
        return "<%s>" % options.testing


class TestWidget3(WidgetBase):
    css_media = ['css1', 'css2', 'css3']
    js_media = ['js1', 'js2', 'js3']


class TagTests(TestCase):
    def test_render(self):
        c = Context()
        t = Template(
            "{% load widget_tags %}"
            "{% widget widgets.tests.TestWidget1 %}")
        self.assertEqual(t.render(c), "test")

    def assertArg(self, args, value, context=Context()):
        t = Template(
            "{%% load widget_tags %%}"
            "{%% widget widgets.tests.TestWidget2 %s %%}"
            % args)
        self.assertEqual(t.render(context), value)

    def test_options(self):
        self.assertArg('--testing "xyz"', "<xyz>")
        self.assertArg('-t "xyz"', "<xyz>")
        self.assertArg('-t xyz', "<abc>", Context({'xyz': 'abc'}))
        self.assertArg('-t 100', "<100>")

    def test_bad_option(self):
        def _bad():
            self.assertArg('-t "xyz" -a 1', "<xyz>")
        self.assertRaises(OptionParserError, _bad)

    def test_media_render(self):
        '''Make sure media isn't duplicated.'''
        c = Context()
        t = Template(
            "{% load widget_tags %}"
            "<head>{% include \"widgets/head.html\" %}</head>"
            "{% widget widgets.tests.TestWidget3 %}"
            "{% widget widgets.tests.TestWidget3 %}")
        wt = WidgetTemplateWrapper(t)

        head = etree.fromstring(wt.render(c))
        self.assertEqual(head.tag, "head")
        self.assertEqual(len(head.getchildren()), 6)

        # Match rendered CSS
        css = head.findall("link")
        self.assertEqual(len(css), 3)
        hrefs = list(e.get('href') for e in css)
        test_widget_3 = TestWidget3()
        self.assertEqual(
            map(lambda x: "%s%s" % (settings.MEDIA_URL, x),
                test_widget_3.css_media),
            hrefs)

        # Match rendered JS
        js = head.findall("script")
        self.assertEqual(len(js), 3)
        srcs = list(e.get('src') for e in js)
        self.assertEqual(
            map(lambda x: "%s%s" % (settings.MEDIA_URL, x),
                test_widget_3.js_media),
            srcs)

    def test_empty_widget(self):
        c = Context()
        t = Template(
            "{% load widget_tags %}"
            "{% include \"widgets/head.html\" %}"
            "{% widget widgets.base.WidgetBase %}")

        wt = WidgetTemplateWrapper(t)
        text = wt.render(c).strip()
        self.assertEqual(text, "")


class TemplateTests(TestCase):
    """Test types of template for finding widgets."""

    def test_extensions(self):
        """Check 3 levels of extension."""
        t = get_template("widgets/test/extenderC.html")
        c = Context()
        wt = WidgetTemplateWrapper(t)
        wt.render(c)
        as_names = [w.as_name.literal for w in wt.widget_nodes]
        as_names = set(as_names)
        self.assertEqual(as_names, set([
            'ablockC',
            'cblockC',
            'ablockB',
            'bblockB',
            'ablockA',
            'cblockA',  # this one actually gets overriden, see note \/
        ]))
        # Worth noting that any block overrides will be ignored.
        # This means we may load MORE JS/CSS than needed, but never less.

    def test_extend_inner_block(self):
        """Check 4 levels of extension, with an inner block overriden."""
        t = get_template("widgets/test/extenderD.html")
        c = Context()
        wt = WidgetTemplateWrapper(t)
        wt.render(c)
        as_names = [w.as_name.literal or w.as_name.var
                    for w in wt.widget_nodes]
        as_names = set(as_names)
        self.assertEqual(as_names, set([
            'ablockC',
            'cblockC',
            'ablockB',
            'bblockB',
            'ablockA',
            'cblockA',
            'dblockD',
        ]))


class WidgetTests(TestCase):
    '''Test individual widgets.'''
    pass  # TODO


if __name__ == '__main__':
    setup_test_environment()
    main()
