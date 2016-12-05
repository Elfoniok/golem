import logging

from autobahn.twisted import ApplicationSession
from autobahn.twisted.wamp import ApplicationRunner
from autobahn.wamp import ProtocolError
from autobahn.wamp import types
from twisted.internet.defer import inlineCallbacks, Deferred

logger = logging.getLogger('golem.rpc')


class RPCAddress(object):

    def __init__(self, protocol, host, port):
        self.protocol = protocol or 'tcp'
        self.host = host
        self.port = port
        self.address = u'{}://{}:{}'.format(self.protocol,
                                            self.host, self.port)

    def __str__(self):
        return str(self.address)

    def __unicode__(self):
        return self.address


class WebSocketAddress(RPCAddress):

    def __init__(self, host, port, realm, ssl=False):
        self.realm = realm
        super(WebSocketAddress, self).__init__(
            u'wss' if ssl else u'ws',
            host, port
        )


class SessionConnector(object):

    def __init__(self, session_class, address, extra=None, serializers=None, ssl=None,
                 proxy=None, headers=None, auto_reconnect=True, log_level='info'):

        self.session = session_class(realm=address.realm)
        self.address = address
        self.extra = extra
        self.serializers = serializers
        self.ssl = ssl
        self.proxy = proxy
        self.headers = headers
        self.log_level = log_level
        self.auto_reconnect = auto_reconnect

    def connect(self):

        runner = ApplicationRunner(
            unicode(self.address),
            realm=self.address.realm,
            extra=self.extra,
            serializers=self.serializers,
            ssl=self.ssl,
            proxy=self.proxy,
            headers=self.headers
        )

        return runner.run(
            self.session,
            start_reactor=False,
            auto_reconnect=self.auto_reconnect,
            log_level=self.log_level
        )


class Session(ApplicationSession):

    def __init__(self, realm, methods=None, events=None):
        self.methods = methods or []
        self.events = events or []

        self.ready = Deferred()
        self.connected = False

        self.config = types.ComponentConfig(realm=realm)
        super(Session, self).__init__(self.config)

    @inlineCallbacks
    def onJoin(self, details):
        yield self.register_methods(self.methods)
        yield self.register_events(self.events)
        self.connected = True
        self.ready.called = False
        self.ready.callback(details)

    @inlineCallbacks
    def onLeave(self, details):
        self.connected = False
        if not self.ready.called:
            self.ready.errback(details or u"Unknown error occurred")

    @inlineCallbacks
    def register_methods(self, methods):
        for method, rpc_name in methods:
            deferred = self.register(method, rpc_name)
            deferred.addErrback(self._on_error)
            yield deferred

    @inlineCallbacks
    def register_events(self, events):
        for method, rpc_name in events:
            deferred = self.subscribe(method, rpc_name)
            deferred.addErrback(self._on_error)
            yield deferred

    @staticmethod
    def _on_error(err):
        logger.error(u"Error in RPC Session: {}".format(err))


class Client(object):

    def __init__(self, session, method_map):

        self.session = session

        for method_name, method_alias in method_map.items():
            setattr(self, method_name, self.make_call(method_alias))

    def make_call(self, method_alias):
        return lambda *a, **kw: self._call(method_alias, *a, **kw)

    def _call(self, method_alias, *args, **kwargs):
        if self.session.connected:
            deferred = self.session.call(method_alias, *args, **kwargs)
            deferred.addErrback(self._on_error)
        else:
            deferred = Deferred()
            deferred.errback(ProtocolError(u"Session is not yet established"))
        return deferred

    @staticmethod
    def _on_error(error):
        logger.error(u"Error in RPC call: {}".format(error))


class Publisher(object):

    def __init__(self, session):
        self.session = session

    def publish(self, event_alias, *args, **kwargs):
        if self.session.connected:
            self.session.publish(event_alias, *args, **kwargs)
        else:
            logger.warn(u"Cannot publish '{}': session is not yet established"
                        .format(event_alias))


def object_method_map(obj, method_map):
    return [
        (getattr(obj, method_name), method_alias)
        for method_name, method_alias in method_map.items()
    ]