import unittest

from nose2.tools import params
from nose2_timer import plugin

try:
    from unittest import mock
except ImportError:
    import mock

class TestTimerPlugin(unittest.TestCase):

    def setUp(self):
        super(TestTimerPlugin, self).setUp()
        self.plugin = plugin.TimerPlugin()
        self.plugin.enabled = True
        self.plugin.timer_ok = 1000
        self.plugin.timer_warning = 2000
        self.plugin.timer_no_color = False
        self.test_mock = mock.MagicMock(name='test')
        self.test_mock.id.return_value = 1
        self.opts_mock = mock.MagicMock(name='opts')

    @unittest.skip('We will not add options this way')
    def test_options(self):
        parser = mock.MagicMock()
        self.plugin.options(parser)
        if not plugin.IS_NT:
            self.assertEquals(parser.add_option.call_count, 8)
        else:
            self.assertEquals(parser.add_option.call_count, 7)

    @unittest.skip('Not gonna work yet')
    def test_configure(self):
        attributes = ('config', 'timer_top_n')
        for attr in attributes:
            self.assertFalse(hasattr(self.plugin, attr))

        self.plugin.configure(self.opts_mock, None)
        for attr in attributes:
            self.assertTrue(hasattr(self.plugin, attr))

    def test_time_taken(self):
        self.assertFalse(hasattr(self.plugin, '_timer'))
        self.assertEquals(self.plugin._time_taken(), 0.0)

        self.plugin.startTest(self.test_mock)
        self.assertTrue(hasattr(self.plugin, '_timer'))
        self.assertNotEquals(self.plugin._time_taken(), 0.0)

    @params(
        ('1', 1000),  # seconds by default
        ('2s', 2000),  # seconds
        ('500ms', 500)  # milliseconds
    )
    def test_parse_time(self, value, expected_ms):
        self.assertEqual(self.plugin._parse_time(value), expected_ms)

    def test_parse_time_error(self):
        self.assertRaises(ValueError, self.plugin._parse_time, '5seconds')

    @params(
        ('timer_ok',),
        ('timer_warning',)
        )
    @unittest.skip('configure is gone')
    def test_parse_time_called(self, option):
        time = '100ms'
        with mock.patch.object(self.plugin, '_parse_time') as parse_time:
            parse_time.return_value = time
            mock_opts = mock.MagicMock(**{option: time})
            self.plugin.configure(mock_opts, None)
            self.assertEqual(getattr(mock_opts, option), time)
            parse_time.has_call(time)

    @params(
        (0.0001, '0.0001s', 'green'),
        (1,      '1.0000s', 'green'),
        (1.0001, '1.0001s', 'yellow'),
        (2.00,   '2.0000s', 'yellow'),
        (2.0001, '2.0001s', 'red')
    )
    @mock.patch("nose2_timer.plugin._colorize")
    def test_colored_time(self, time_taken, expected, color, colored_mock):
        self.plugin._colored_time(time_taken, color)
        colored_mock.assert_called_once_with(expected, color)

    @mock.patch("nose2_timer.plugin._colorize")
    def test_no_color_option(self, colored_mock):
        self.plugin.timer_no_color = True
        self.assertEqual(self.plugin._colored_time(1), "1.0000s")
        self.assertFalse(colored_mock.called)

    @params(
        ('warning', 0.5, False),
        ('warning', 1.5, True),
        ('error', 1.5, False),
        ('error', 2.5, True),
    )
    @unittest.skip('addSuccess is gone now')
    def test_timer_fail_option_warning_pass(self, timer_fail_level, time_taken,
                                            fail_expected):
        self.plugin.timer_fail = timer_fail_level
        self.plugin.multiprocessing_enabled = False
        with mock.patch.object(self.plugin, '_time_taken') as _time_taken:
            _time_taken.return_value = time_taken
            self.plugin.startTest(self.test_mock)
            self.plugin.addSuccess(self.test_mock)
            self.assertEqual(self.test_mock.fail.called, fail_expected)
