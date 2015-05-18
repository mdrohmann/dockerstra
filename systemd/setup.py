import ez_setup
ez_setup.use_setuptools()

import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

setup(
    name='docker_meta',
    description='Automatically start docker containers',
    author='Martin C Drohmann',
    author_email='mcd@askthevotegoat.com',
    scripts=['scripts/docker_start.py'],
    version='1.2',
    install_requires=['docker-py', 'pyyaml'],
    license='LICENSE',
    packages=find_packages(),
    cmdclass={'test': PyTest},
    )
