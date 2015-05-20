from pkg_resources import get_distribution


__all__ = [
    'utils', 'read_configuration',
    'run_configuration', 'DockerContainer',
    '__version__']

__version__ = get_distribution(__name__).version


# vim:set ft=python sw=4 et spell spelllang=en:
