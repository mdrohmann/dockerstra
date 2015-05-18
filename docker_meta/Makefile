.PHONY: publish test develop

BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
IS_DEVELOPMENT := $(filter development feature/%, $(BRANCH))
TAG := $(if $(IS_DEVELOPMENT), "-b devel")

publish:
		python setup.py egg_info $(TAG) sdist bdist_egg upload -r internal

test:
	py.test -s test/

develop:
		python setup.py egg_info $(TAG) develop;
