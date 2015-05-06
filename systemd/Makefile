.PHONY: publish test develop

publish:
	test "`git rev-parse --abbrev-ref HEAD`" = "development" && TAG="-b .devel"; \
		python setup.py egg_info $$TAG sdist bdist_egg upload -r internal

test:
	py.test -s test/

develop:
	test "`git rev-parse --abbrev-ref HEAD`" = "development" && TAG="-b .devel"; \
		python setup.py egg_info $$TAG develop;
