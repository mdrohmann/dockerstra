.PHONY: publish test

publish:
	[ "$(git branch)" == "development" ] && TAG="-b devel"
	python setup.py egg_info $$TAG sdist bdist_egg publish -r internal

test:
	py.test -s test/

