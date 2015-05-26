# -*- coding: utf-8 -*-

import hashlib
import platform
import time
import traceback
from cStringIO import StringIO

from junit_xml import TestCase, TestSuite
from docker_meta.utils import get_timestamp


class CaseBase(object):
    """
    base class for testrunner cases representing one or more test cases.
    """

    def __init__(self, name, parent, classname=None):
        self.parent = parent
        self.name = name
        self.classname = classname

    def create_unit_call(self):
        """
        returns the configuration for a unit call.
        """

        # calls self._
        pass

    def run_test(self):
        """
        runs the actual test.  This needs to be implemented in the derived
        class.
        """

        raise NotImplementedError(
            "Please implement this in your derived class.")

    def _run_unit_test(self, args):
        envs = self.parent.compute_environment_injections()

        args = self.create_unit_call(self)
        args.environment = envs

        main_run(args)

    def run_case(self, case):
        """
        runs a single test case and returns a junit_xml.TestCase object with
        the results
        """

        failure = None
        stdout, stderr = StringIO(), StringIO()

        start = time.time()
        try:
            self.run_test(stdout, stderr)
        except Exception as e:
            failure = (
                "FAILURE: {}".format(str(e)),
                traceback.format_exc(3))
        except SystemExit as e:
            failure = (
                "FAILURE: test return with error code: {}\n{}"
                .format(e.error_code, str(e)),
                traceback.format_exc(3))
        end = time.time()
        elapsed = (end - start)

        res = TestCase(
            self.name, self.classname, elapsed_sec=elapsed,
            stdout=stdout.getvalue(), stderr=stderr.getvalue())
        if failure:
            res.add_failure_info(*failure)

        return res

    def run(self):
        rescases = []
        for case in self.cases:
            res = self.run_case(case)
            rescases.append(res)
        return rescases


class DaemonCase(CaseBase):
    """
    a test case for a daemon
    """

    def __init__(self, name):
        self.cases = self.collect()
        CaseBase.__init__(self, name, 'daemon')

    def run_test(self):
        raise NotImplementedError()


class DefaultSingleCase(CaseBase):
    """
    a test case for default single job
    """

    def __init__(self, name):
        self.cases = self.collect()
        CaseBase.__init__(self, name, 'single')

    def run_test(self):
        raise NotImplementedError()


class JunitCase(CaseBase):
    """
    a test case for a script that produces a junit file itself eg., a pytest
    run
    """

    def __init__(self, name):
        self.cases = self.collect()
        CaseBase.__init__(self, name, 'junit')

    def run_test(self):
        raise NotImplementedError()


class Suite(object):
    """
    handles the jobs to execute, and outputs their information.
    """

    def __init__(self, unitcommand, config):
        self.config = config
        self.unitcommand = unitcommand
        self._runs = self._collect_runs(self.unitcommand)
        self._digest = None
        self._suites = None

    def default_environment_injections(self):
        """
        these are the tempid and the modes.
        """
        modes = self.config.active_modes()
        return dict(
            tempid=self.tempid(),
            modes=modes)

    def output_xml(self, filename):
        if not self._suite:
            raise RuntimeError(
                "You need to call run_all() before printing the results")

        with open(filename, 'w') as fh:
            TestSuite.to_file(
                fh, self._suites, prettyprint=False, encoding='utf-8')

    def tempid(self, long=False):
        if not self._digest:
            self._digest = hashlib.md5(self.unitcommand).hexdigest()[0:10]
        if long:
            return '{}_{}'.format(self.unitcommand, self._digest)
        else:
            return self._digest

    def run_all(self):
        # create the runs:
        timestamp = get_timestamp()

        for suiten, suite in enumerate(self.suites):
            rescases = suite.run_all()

            suite = TestSuite(
                self.name,
                rescases, hostname=platform.node(),
                id='_'.join([self.tempid(long=True), suiten]),
                timestamp=timestamp)
            self._suites.append(suite)

# vim:set ft=python sw=4 et spell spelllang=en:
