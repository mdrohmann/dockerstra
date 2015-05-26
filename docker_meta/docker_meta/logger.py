import json
import logging.config
import sys
from StringIO import StringIO

test_streams = {}
default_config = {}


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
        infofiles=None, errorfiles=None, verbosity=0, debug=False, test=False,
        incremental=False):
    config = {
        'version': 1,
        'incremental': incremental,
        'disable_existing_loggers': (not incremental),
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
        },
        'loggers': {
            'root': {
                'level': 'NOTSET',
                'handlers': ['null'],
            },
            'docker_meta': {
                'level': 'INFO',
                'propagate': False,
            },
        },
    }

    stream_configs, handlers = _get_streams(
        infofiles, errorfiles, test)

    if debug:
        config['loggers']['docker_meta']['level'] = 'DEBUG'

    _update_handlers(config, stream_configs, handlers)

    return config


def _update_handlers(config, stream_configs, handlers):
    for sc, name, typ in stream_configs:
        if typ == 'info':
            tc = {
                name: {
                    'level': 'DEBUG',
                    'formatter': 'default',
                    'filters': ['info_only', 'output_filter'],
                    }
            }
        elif typ == 'error':
            tc = {
                name: {
                    'level': 'WARNING',
                    'formatter': 'errors',
                    }
            }
        tc[name].update(sc)
        config['handlers'].update(tc)

    config['loggers']['docker_meta']['handlers'] = handlers


def _get_streams(infofiles, errorfiles, test):
    if test:
        info_sc, info_h = _get_test_stream('info')
        error_sc, error_h = _get_test_stream('error')
        res = [info_sc, error_sc]
        handlers = [info_h, error_h]
    else:
        res = []
        handlers = []
        _update_single_stream(infofiles, res, sys.stdout, 'info', handlers)
        _update_single_stream(errorfiles, res, sys.stderr, 'error', handlers)
    return res, handlers


def _update_single_stream(infofiles, res, default, typ, handlers):
    if infofiles is None:
        infofiles = [default]
    if isinstance(infofiles, basestring):
        infofiles = [infofiles]
    for n, infofile in enumerate(infofiles):
        info_stream_config = _get_stream_for_file(
            infofile)
        name = '{}_stream'.format(typ)
        if n > 0:
            name += str(n + 1)
        res.append((info_stream_config, name, typ))
        handlers.append(name)


def _get_test_stream(streamtype):
    test_streams[streamtype] = StringIO()
    stream_config = {
        'class': 'logging.StreamHandler',
        'stream': test_streams[streamtype],
    }
    handler = '{}_stream'.format(streamtype)
    return (stream_config, handler, streamtype), handler


def _get_stream_for_file(filename, default=sys.stdout):
    if isinstance(filename, basestring) and filename:
        stream_config = {
            'class': 'logging.FileHandler',
            'filename': filename,
        }
    else:
        stream_config = {
            'class': 'logging.StreamHandler',
            'stream': (filename or default),
        }
    return stream_config


def configure_logger(*args, **kwargs):
    """
    use this to configure the default logger.
    """
    config = _get_logger_configuration(*args, **kwargs)
    default_config.update(config)
    logging.config.dictConfig(config)


def reset_logger():
    """
    resets to the default logger
    """
    if default_config:
        logging.config.dictConfig(default_config)
    else:
        raise RuntimeError("Logger has not been initialized yet.")


def update_logger(*args, **kwargs):
    """
    use this to temporarily change the logger.
    """
    config = _get_logger_configuration(*args, **kwargs)
    logging.config.dictConfig(config)


def _test_stream_lines(stream):
    return test_streams.get(stream, StringIO()).getvalue().rstrip()


def info_lines():
    return _test_stream_lines('info')


def error_lines():
    return _test_stream_lines('error')


def last_info_line(n=1):
    return _last_stream_line('info', n)


def last_error_line(n=1):
    return _last_stream_line('error', n)


def _last_stream_line(stream, n=1):
    rsargs = [x for x in ['\n', n] if x is not None]
    infos = _test_stream_lines(stream).rsplit(*rsargs)
    if n is not None and len(infos) > 1:
        res = infos[1:]
    else:
        res = infos
    return res

# vim:set ft=python sw=4 et spell spelllang=en:
