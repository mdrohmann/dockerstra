import json
import logging.config
import sys
from StringIO import StringIO

test_streams = {}


class OutputFilter(logging.Filter):
    """
    filters and prettifies the output generated by several docker commands
    """

    def __init__(self, verbosity):
        self.verbosity = verbosity
        self.last_pull_status = ''
        self.skipped_pull_messages = 0

    def filter(self, record):
        if hasattr(record, 'type') and record.type == 'output':
            if self.verbosity < 1:
                return False

            msg = record.msg
            if msg == '':
                return False

            if record.cmd == 'build':
                try:
                    md = json.loads(msg)
                except:
                    return False
                record.msg = md.get('stream', '')

            elif record.cmd == 'execute':
                record.msg = record.msg.strip()

            elif record.cmd == 'create_container':
                record.msg = 'Created image with Id {}'.format(msg['Id'])
                if msg['Warnings']:
                    record.msg += '\n' + msg['Warnings']

            elif record.cmd == 'pull':
                try:
                    md = json.loads(msg)
                except:
                    return False
                status = md.get('status', None)
                if status is None:
                    return False

                if self.last_pull_status == status:
                    if self.verbosity == 1:
                        return False
                    elif self.verbosity == 2:
                        self.skipped_pull_messages += 1
                        if self.skipped_pull_messages % 20 != 0:
                            return False

                    record.msg = repr(md.get('progressDetail', {}))

                self.last_pull_status = status
                out = {'id': '', 'status': '', 'progressDetail': ''}
                out.update(md)
                record.msg = '({id}) {status}: {progressDetail}'.format(**out)

        record.msg = record.msg.strip()
        return True


class MaxFilter(logging.Filter):
    """
    lets only messages pass that are less or equally critical as ``maxlevel``.
    """

    def __init__(self, maxlevel):
        self.maxlevel = maxlevel

    def filter(self, record):
        return record.levelno <= self.maxlevel


def _get_logger_configuration(
        infofile=None, errorfile=None, verbosity=0, debug=False, test=False):
    config = {
        'version': 1,
        'incremental': False,
        'disable_existing_loggers': True,
        'formatters': {
            'default': {
                'format': '%(asctime)s: %(levelname)s: %(message)s'
            },
            'errors': {
                'format':
                    '%(asctime)s: %(levelname)s: %(filename)s: %(message)s'
            },
        },
        'filters': {
            'info_only': {
                '()': MaxFilter,
                'maxlevel': logging.INFO,
            },
            'output_filter': {
                '()': OutputFilter,
                'verbosity': verbosity,
            }
        },
        'handlers': {
            'null': {
                'level': 'DEBUG',
                'class': 'logging.NullHandler',
            },
            'info_stream': {
                'level': 'DEBUG',
                'formatter': 'default',
                'filters': ['info_only', 'output_filter'],
            },
            'error_stream': {
                'level': 'WARNING',
                'formatter': 'errors',
            },
        },
        'loggers': {
            'root': {
                'level': 'NOTSET',
                'handlers': ['null'],
            },
            'docker_meta': {
                'level': 'INFO',
                'propagate': False,
                'handlers': ['info_stream', 'error_stream'],
            },
        },
    }

    if test:
        test_streams['info'] = StringIO()
        test_streams['errors'] = StringIO()
        info_stream_config = {
            'class': 'logging.StreamHandler',
            'stream': test_streams['info'],
        }
        error_stream_config = {
            'class': 'logging.StreamHandler',
            'stream': test_streams['errors'],
        }
    else:
        if infofile:
            info_stream_config = {
                'class': 'logging.FileHandler',
                'filename': infofile,
            }
        else:
            info_stream_config = {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
            }
        if errorfile:
            error_stream_config = {
                'class': 'logging.FileHandler',
                'filename': errorfile,
            }
        else:
            error_stream_config = {
                'class': 'logging.StreamHandler',
                'stream': sys.stderr,
            }

    if debug:
        config['loggers']['docker_meta']['level'] = 'DEBUG'

    config['handlers']['info_stream'].update(info_stream_config)
    config['handlers']['error_stream'].update(error_stream_config)

    return config


def configure_logger(*args, **kwargs):
    config = _get_logger_configuration(*args, **kwargs)
    logging.config.dictConfig(config)


def _test_stream_lines(stream):
    return test_streams.get(stream, StringIO()).getvalue().rstrip()


def info_lines():
    return _test_stream_lines('info')


def error_lines():
    return _test_stream_lines('errors')


def last_info_line(n=1):
    return _last_stream_line('info', n)


def last_error_line(n=1):
    return _last_stream_line('errors', n)


def _last_stream_line(stream, n=1):
    rsargs = [x for x in ['\n', n] if x is not None]
    infos = _test_stream_lines(stream).rsplit(*rsargs)
    if n is not None and len(infos) > 1:
        res = infos[1:]
    else:
        res = infos
    return res

# vim:set ft=python sw=4 et spell spelllang=en:
