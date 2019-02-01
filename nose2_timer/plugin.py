import json
import logging
import os
import re
import timeit

from nose2 import result
from nose2.events import Plugin

from collections import OrderedDict

try:
    import termcolor
except ImportError:
    termcolor = None

try:
    import colorama
    TERMCOLOR2COLORAMA = {
        'green': colorama.Fore.GREEN,
        'yellow': colorama.Fore.YELLOW,
        'red': colorama.Fore.RED,
    }
except ImportError:
    colorama = None

# define constants
IS_NT = os.name == 'nt'

log = logging.getLogger('nose.plugin.timer')


def _colorize(val, color):
    """Colorize a string using termcolor or colorama.

    If any of them are available.
    """
    if termcolor is not None:
        val = termcolor.colored(val, color)
    elif colorama is not None:
        val = TERMCOLOR2COLORAMA[color] + val + colorama.Style.RESET_ALL

    return val


class TimerPlugin(Plugin):
    """This plugin provides test timings."""
    configSection = 'timer'
    commandLineSwitch = ('T', 'timer', 'Time test cases')

    score = 1

    time_format = re.compile(r'^(?P<time>\d+)(?P<units>s|ms)?$')
    _timed_tests = {}

    def __init__(self):
        self._threshold = None
        self.timer_top_n = self.config.as_int('slowest-n', default=-1)
        self.timer_ok = self._parse_time(self.config.as_int('time-ok', 
                                         default=5))
        self.timer_warning = self._parse_time(
            self.config.as_int('time-warn', default=10))
        self.timer_filter = self._parse_filter(
            self.config.as_str('time-filter', default=None))
        self.timer_fail = self.config.as_str('timer-fail', default='error')
        self.timer_no_color = self.config.as_bool('colorize', default=True)
        self.json_file = self.config.as_str('log-file', default=None)
        self._outcome = ''
        self.options()        

    @property
    def threshold(self):
        """Get maximum test time allowed when --timer-fail option is used."""
        if self._threshold is None:
            self._threshold = {
                'error': self.timer_warning,
                'warning': self.timer_ok,
            }[self.timer_fail]
        return self._threshold

    def _time_taken(self):
        if hasattr(self, '_timer'):
            taken = timeit.default_timer() - self._timer
        else:
            # Test died before it ran (probably error in setup()) or
            # success/failure added before test started probably due to custom
            # `TestResult` munging.
            taken = 0.0
        return taken

    def _parse_time(self, value):
        """Parse string time representation to get number of milliseconds.
        Raises the ``ValueError`` for invalid format.
        """
        try:
            # Default time unit is a second, we should convert it to
            # milliseconds.
            return int(value) * 1000
        except ValueError:
            # Try to parse if we are unlucky to cast value into int.
            m = self.time_format.match(value)
            if not m:
                raise ValueError("Could not parse time represented by "
                                 "'{t}'".format(t=value))
            time = int(m.group('time'))
            if m.group('units') != 'ms':
                time *= 1000
            return time

    @staticmethod
    def _parse_filter(value):
        """Parse timer filters."""
        return value.split(',') if value is not None else None

    def _color_to_filter(self, color):
        """Get filter name by a given color."""
        return {
            'green': 'ok',
            'yellow': 'warning',
            'red': 'error',
        }.get(color)
        
    def _get_result_color(self, time_taken):
        """Get time taken result color."""
        time_taken_ms = time_taken * 1000
        if time_taken_ms <= self.timer_ok:
            color = 'green'
        elif time_taken_ms <= self.timer_warning:
            color = 'yellow'
        else:
            color = 'red'

        return color

    def _colored_time(self, time_taken, color=None):
        """Get formatted and colored string for a given time taken."""
        if self.timer_no_color:
            return "{0:0.4f}s".format(time_taken)

        return _colorize("{0:0.4f}s".format(time_taken), color)

    def _format_report_line(self, test, time_taken, color, status, percent):
        """Format a single report line."""
        return "[{0}] {3:04.2f}% {1}: {2}".format(
            status, test, self._colored_time(time_taken, color), percent
        )

    def _register_time(self, test, status=None):
        time_taken = self._time_taken()

        self._timed_tests[test.id()] = {
            'time': time_taken,
            'status': status,
        }
        return time_taken


    def register(self):
        super(TimerPlugin, self).register()

    # Multiprocess handling
    def registerInSubprocess(self, event):
        event.pluginClasses.append(self.__class__)

    def startTest(self, event):
        """Initializes a timer before starting a test."""
        self._timer = timeit.default_timer()

    def afterSummaryReport(self, event):
        """Report the test times."""

        sorted_times = sorted(self._timed_tests.items(),
                   key=lambda item: item[1]['time'],
                   reverse=True)
    

        if self.json_file:
            dict_type = OrderedDict if self.timer_top_n else dict
            with open(self.json_file, 'w') as f:
                json.dump({'tests': dict_type((k, v) for k, v in sorted_times)}, f)

        total_time = sum([vv['time'] for kk, vv in sorted_times])


        for i, (test, time_and_status) in enumerate(sorted_times):
            time_taken = time_and_status['time']
            status = time_and_status['status']
            if i < self.timer_top_n or self.timer_top_n == -1:
                color = self._get_result_color(time_taken)
                percent = 0 if total_time == 0 else time_taken/total_time*100
                line = self._format_report_line(test,
                                                time_taken,
                                                color,
                                                status,
                                                percent)
                _filter = self._color_to_filter(color)
                if (self.timer_filter is None or _filter is None or
                        _filter in self.timer_filter):
                    event.stream.writeln(line)

    def testOutcome(self, event):
        """
        Handles test outcomes to register timings
        """
        # No handlng for skipped tests yet
        test = event.test
        if event.outcome == result.ERROR:
            # self._register_time(test, 'error')
            self._outcome = event.outcome
        elif event.outcome == result.FAIL:
            # This probably won't work well with expected failures yet
            # self._register_time(test, 'fail')
            self._outcome = event.outcome

    def setTestOutcome(self, event):
        """
        Sets test outcomes in order to mark slow running tests as failures

        """
        test = event.test
        if event.outcome == result.PASS:
            self._register_time(test, 'success')
            time_taken = self._time_taken()
            if self.timer_fail is not None and time_taken * 1000.0 > self.threshold:
                print('I hit the timer fail condition yo')
                # We have to set the outcome as a failure
                event.reason = 'Test was too slow (took {0:0.4f}s, threshold was '\
                                '{1:0.4f}s)'.format(time_taken, self.threshold / 1000.0)                                
                event.outcome = result.FAIL
                event.expected = False # We don't expect these to fail
                # self._register_time(test, 'fail')
                self._outcome = event.outcome
            else:
                # self._register_time(test, 'success')
                self._outcome = event.outcome

    def stopTest(self, event):
        test = event.test
        self._register_time(test, self._outcome)


    # def beforeSummaryReport(self, event):
    #     """Called before the first test is run."""
    #     def _add_success(self, event, test):
    #         """Called when a test passes."""
    #         if event.showAll:
    #             output = 'ok'
    #             time_taken = self._timed_tests.get(test.id())['time']
    #             if time_taken is not None:
    #                 color = self._get_result_color(time_taken)
    #                 output += ' ({0})'.format(self._colored_time(time_taken,
    #                                                              color))
    #             event.stream.writeln(output)
    #         elif event.dots:
    #             event.stream.write('.')
    #             event.stream.flush()

    #     # monkeypatch the result
    #     event.addSuccess = lambda test: _add_success(event, test)
    #     event._timed_tests = self._timed_tests

    # TODO: Make these command-line options behave the nose2 'way'
    def options(self, env=os.environ):
        """Register commandline options."""

        # timer top n
        self.addArgument(
            callback=self.timer_top_n,
            short_opt='',
            long_opt='timer-top-n',
            help_text=(
                "When the timer plugin is enabled, only show the N tests that "
                "consume more time. The default, -1, shows all tests."
            ))
        
        self.addArgument(
            callback=self.json_file,
            short_opt='O',
            long_opt="timer-json-file",
            help_text=(
                "Save the results of the timing and status of each tests in "
                "said Json file."
            ),
        )

        _time_units_help = ("Default time unit is a second, but you can set "
                            "it explicitly (e.g. 1s, 500ms)")

        # timer ok
        self.addArgument(
            callback=self.timer_ok,
            short_opt='',
            long_opt="timer-ok",
            help_text=(
                "Normal execution time. Such tests will be highlighted in "
                "green. {units_help}.".format(units_help=_time_units_help)
            ),
        )

        # time warning
        self.addArgument(
            callback=self.timer_warning,
            short_opt='W',
            long_opt="timer-warning",
            help_text=(
                "Warning about execution time to highlight slow tests in "
                "yellow. Tests which take more time will be highlighted in "
                "red. {units_help}.".format(units_help=_time_units_help)
            ),
        )

        # Windows + nosetests does not support colors (even with colorama).
        if not IS_NT:
            self.addArgument(
                callback=self.timer_no_color,
                short_opt='',
                long_opt="timer-no-color",
                help_text="Don't colorize output (useful for non-tty output).",
            )

        # timer filter
        self.addArgument(
            callback=self.timer_filter,
            short_opt='',
            long_opt="timer-filter",
            help_text="Show filtered results only (ok,warning,error).",
        )

        # timer fail
        self.addArgument(
            callback=self.timer_fail,
            short_opt='',
            long_opt="timer-fail",
            help_text="Fail tests that exceed a threshold (warning,error)",
        )
