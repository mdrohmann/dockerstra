import pytest
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.internet.ssl import CertificateOptions, PrivateCertificate
from twisted.python.modules import getModule


class WebClientContextFactory(CertificateOptions):

    def __init__(self):
        pem = (
            getModule(__name__).filePath.parent()
            .sibling('certs').child('ssl.cgit.main.pem').getContent())
        pem = getModule(__name__).filePath.sibling('invalid.pem').getContent()
        pc = PrivateCertificate.loadPEM(pem)
        CertificateOptions.__init__(self, trustRoot=pc)

    def getContext(self, hostname, port):
        return CertificateOptions.getContext(self)


@pytest.fixture
def url(request):
    return request.param


@pytest.fixture
def agent_call(url):
    url, ssl = url
    if ssl:
        contextFactory = WebClientContextFactory()
        agent = Agent(reactor, contextFactory)
    else:
        agent = Agent(reactor)

    headers = Headers(
        {'User-Agent': ['Twisted Webbot'],
         'Content-Type': ['text/x-greeting']})

    d = agent.request('HEAD', url, headers=headers)
    return d


def expect_header(version, code, sts=False):

    def header_expectations(response):
        assert response.version == version
        assert response.code == code
        sts_header = response.headers.getRawHeaders(
            'strict-transport-security')
        if sts:
            assert sts_header
        else:
            assert not sts_header

    return header_expectations


def error(failure):
    import pudb; pudb.set_trace()
    print failure
    assert False


# TODO: add a test, where the authentication fails...
@pytest.mark.parametrize(
    'url, expected_header',
    [(('http://cgit.main', False),
      expect_header(('HTTP', 1, 1), 200, sts=False)),
     (('https://ssl.cgit.main', True),
      expect_header(('HTTP', 1, 1), 200, sts=True)),
     (('http://ssl.cgit.main', True),
      expect_header(('HTTP', 1, 1), 301, sts=False)),
     (('https://cgit.main', True),
      expect_header(('HTTP', 1, 1), 200, sts=True)),
     (('https://ssl2.cgit.main', True),
      expect_header(('HTTP', 1, 1), 200, sts=True)),
     ])
def test_header_responses(agent_call, url, expected_header):
    agent_call.addCallbacks(expected_header, error)
    return agent_call


# vim:set ft=python sw=4 et spell spelllang=en:
