"""
.. module:: listener 
:platform: Unix
:synopsis: This module provides an eventsource listener based on tornado

.. moduleauthor:: Bernard Pratz <guyzmo@hackable-devices.org>

.. note::
resources:
    - http://stackoverflow.com/questions/10665569/websocket-event-source-implementation-to-expose-a-two-way-rpc-to-a-python-dj
    - http://stackoverflow.com/questions/8812715/using-a-simple-python-generator-as-a-co-routine-in-a-tornado-async-handler
    - http://dev.w3.org/html5/eventsource/#event-stream-interpretation
    - http://github.com/guyzmo/event-source-library/
"""

import os
import sys
import time
import logging
import argparse
import traceback
import collections

log = logging.getLogger("eventsource.listener")

import httplib
from tornado.escape import json_decode, json_encode
import tornado.web
import tornado.httpserver
import tornado.ioloop

# Event base

class Event(object):
    """
    Class that defines an event, its behaviour and the matching actions

    Members defined by base Event:
        - **target** is the token that matches an event source channel
        - **action** contains the name of the action (which shall be in `ACTIONS`)
        - **value** contains a list of every lines of the value to be parsed

    Static members:
        - content_type field is the Accept header value that is returned on new connections
        - **ACTIONS** contains the list of acceptable POST targets.
        - Actions defined in base Event:
            - **LISTEN** is the GET event that will open an event source communication
            - **FINISH** is the POST event that will end a communication started by `LISTEN`
            - **RETRY** is the POST event that defines reconnection timeouts for the client
    """
    content_type = "text/plain"

    LISTEN = "poll"
    FINISH = "close"
    RETRY = "retry"
    ACTIONS=[FINISH]

    def get_value(self):
        """Property to encapsulate processing on value"""
        return self._value

    def set_value(self, v):
        self._value = v

    value = property(get_value,set_value)

    id = None

    def __init__(self, target, action, value=None):
        """
        Creates a new Event object with
        :param target: a string matching an open channel
        :param action: a string matching an action in the ACTIONS list
        :param value: a value to be embedded
        """
        self.target = target
        self.action = action
        self.set_value(value)

class EventId(object):
    """
    Class that defines an event with an id
        - defines field `id` using property, using method `get_id()`
    """
    cnt = 0

    def get_id(self):
        """Method to create id generation behaviour"""
        if self.cnt == EventId.cnt:
            self.cnt = EventId.cnt
            EventId.cnt+=1
        return self.cnt

    id = property(get_id)

# Reusable events

class StringEvent(Event):
    """
    Class that defines a multiline string Event
        - overloads `Event.get_value()`, and associates it using a property
        - adds a "ping" event
    """
    ACTIONS=["ping",Event.FINISH]
    def get_value(self):
        return [line for line in self._value.split('\n')]

    value = property(get_value,Event.set_value)

class JSONEvent(Event):
    """
    Class that defines a JSON-checked Event
        - overloads `Event.get_value()` and `Event.set_value()`, and associates it using a property
        - adds a "ping" event
        - defines content_type to `application/json`
    """
    content_type = "application/json"

    LISTEN = "poll"
    FINISH = "close"
    ACTIONS=["ping",FINISH]

    def get_value(self):
        return [json_encode(self._value)]

    def set_value(self, v):
        self._value = json_decode(v)

    value = property(get_value,set_value)

class StringIdEvent(StringEvent,EventId):
    """
    Class that defines a Multiline String Event with id generation
    """
    ACTIONS=["ping",Event.RETRY,Event.FINISH]

    id = property(EventId.get_id)

class JSONIdEvent(JSONEvent,EventId):
    """
    Class that defines a JSON-checked Event with id generation
    """
    content_type = JSONEvent.content_type
    ACTIONS=["ping",Event.RETRY,Event.FINISH]
    
    id = property(EventId.get_id)

# EventSource mechanism

class EventSourceHandler(tornado.web.RequestHandler):
    def initialize(self, event_class=StringEvent, keepalive=0):
        """
        Takes an Event based class to define the event's handling
        :param event_class: defines the kind of event that is expected
        :param keepalive: time lapse to wait for sending keepalive messages. If `0`, keepalive is deactivated.
        """
        self._connected = {}
        self._events = {}
        self._event_class = event_class
        self._retry = None
        if keepalive is not 0:
            self._keepalive = tornado.ioloop.PeriodicCallback(self.push_keepalive, int(keepalive))
        else:
            self._keepalive = None

    # Tools

    @tornado.web.asynchronous
    def push_keepalive(self):
        """
        callback function called by `tornado.ioloop.PeriodicCallback`
        """
        log.debug("push_keepalive()")
        self.write(": keepalive %s\r\n\r\n" % (unicode(time.time())))
        self.flush()

    def push(self, event):
        """
        For a given event, write event-source outputs on current handler

        :param event: Event based incoming event
        """
        log.debug("push(%s,%s,%s)" % (event.id,event.action,event.value))
        if hasattr(event, "id"):
            self.write("id: %s\r\n" % (unicode(event.id)))
        if self._retry is not None:
            self.write("retry: %s\r\n" % (unicode(self._retry)))
            self._retry = None
        self.write("event: %s\r\n" % (unicode(event.action)))
        for line in event.value:
            self.write("data: %s\r\n" % (unicode(line),))
        self.write("\r\n")
        self.flush()

    def buffer_event(self, target, action, value=None):
        """
        creates and store an event for the target

        :param target: string identifying current target
        :param action: string matching one of Event.ACTIONS
        :param value: string containing a value
        """
        self._events[target].append(self._event_class(target, action, value))

    def is_connected(self, target):
        """
        Tells whether an eventsource channel identified by `target` is opened.

        :param target: string identifying a given target
        @return true if target is connected
        """
        return target in self._connected.values()

    def set_connected(self, target):
        """
        registers target as being connected

        :param target: string identifying a given target

        this method will add target to the connected list and create an empty event buffer
        """
        log.debug("set_connected(%s)" % (target,))
        self._connected[self] = target
        self._events[target] = collections.deque()

    def set_disconnected(self):
        """
        unregisters current handler as being connected

        this method will remove target from the connected list and delete the event buffer
        """
        target = None
        try:
            target = self._connected[self]
            log.debug("set_disconnected(%s)" % (target,))
            if self._keepalive:
                self._keepalive.stop()
            del(self._events[target])
            del(self._connected[self])
        except Exception, err:
            log.error("set_disconnected(%s,%s): %s", str(self), target, err)

    def write_error(self, status_code, **kwargs):
        """
        Overloads the write_error() method of RequestHandler, to
        support more explicit messages than only the ones from httplib.
        This will end the current eventsource channel.

        :param status_code: error code to be returned
        :param mesg: specific message to output (if non-present, httplib error message will be used)
        :param exc_info: displays exception trace (if debug mode is enabled)
        """
        if self.settings.get("debug") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            if 'mesg' in kwargs:
                self.finish("<html><title>%(code)d: %(message)s</title>" 
                            "<body>%(code)d: %(mesg)s</body></html>\n" % {
                        "code": status_code,
                        "message": httplib.responses[status_code],
                        "mesg": kwargs["mesg"],
                        })
            else:
                self.finish("<html><title>%(code)d: %(message)s</title>" 
                            "<body>%(code)d: %(message)s</body></html>\n" % {
                        "code": status_code,
                        "message": httplib.responses[status_code],
                        })

    # Synchronous actions

    def post(self,action,target):
        """
        Triggers an event

        :param action: string defining the type of event
        :param target: string defining the target handler to send it to
        :returns: HTTP error 404 if `target` is not connected
        :returns: HTTP error 404 if `action` is not in Event.ACTIONS
        :returns: HTTP error 400 if data is not properly formatted.

        this method will look for the request body to get post's data.
        """
        log.debug("post(%s,%s)" % (target,action))
        self.set_header("Accept", self._event_class.content_type)
        if target not in self._connected.values():
            self.send_error(404,mesg="Target is not connected")
        elif action not in self._event_class.ACTIONS:
            self.send_error(404,mesg="Unknown action requested")
        else:
            try:
                self.buffer_event(target,action,self.request.body)
                tornado.ioloop.IOLoop.instance().add_callback(self._event_loop)
            except ValueError, ve:
                self.send_error(400,mesg="Data is not properly formatted: <br />%s" % (ve,))

    # Asynchronous actions
    
    def _event_generator(self,target):
        """
        parses all events buffered for target and yield them

        :param target: string matching the token of a target
        :yields: each buffered event
        """
        while len(self._events[target]) != 0:
            yield self._events[target].pop()
        
    def _event_loop(self):
        """
        for target matching current handler, gets and forwards all events
        until Event.FINISH is reached, and then closes the channel.
        """
        if self.is_connected(self.target):
            for event in self._event_generator(self.target):
                if self._event_class.RETRY in self._event_class.ACTIONS:
                    if event.action == self._event_class.RETRY:
                        try:
                            self._retry = int(event.value[0])
                            continue
                        except ValueError:
                            log.error("incorrect retry value: %s" % (event.value,))
                if event.action == self._event_class.FINISH:
                    self.set_disconnected()
                    self.finish()
                    return
                self.push(event)

    @tornado.web.asynchronous
    def get(self,action,target):
        """
        Opens a new event_source connection and wait for events to come

        :returns: error 423 if the target token already exists
        Redirects to / if action is not matching Event.LISTEN.
        """
        log.debug("get(%s,%s)" % (target, action))
        if action == self._event_class.LISTEN:
            self.set_header("Content-Type", "text/event-stream")
            self.set_header("Cache-Control", "no-cache")
            self.target = target
            if self.is_connected(target):
                self.send_error(423,mesg="Target is already connected")
                return
            self.set_connected(target)
            if self._keepalive:
                self._keepalive.start()
        else:
            self.redirect("/",permanent=True)
        
    def on_connection_close(self):
        """
        overloads RequestHandler's on_connection_close to disconnect
        currents handler on client's socket disconnection.
        """
        log.debug("on_connection_close()")
        self.set_disconnected()

###

def start():
    """helper method to create a commandline utility"""
    parser = argparse.ArgumentParser(prog=sys.argv[0],
                            description="Event Source Listener")
    parser.add_argument("-H",
                        "--host",
                        dest="host",
                        default='0.0.0.0',
                        help='Host to bind on')
    # PORT ARGUMENT
    parser.add_argument("-P",
                        "--port",
                        dest="port",
                        default='8888',
                        help='Port to bind on')

    parser.add_argument("-K",
                        "--keyfile",
                        dest="ssl_keyfile",
                        default='',
                        help='Path to Key file\nif specified with --certfile, SSL is enabled')

    parser.add_argument("-C",
                        "--certfile",
                        dest="ssl_certfile",
                        default='',
                        help='Path to CA Cert file\nif specified with --keyfile, SSL is enabled')

    parser.add_argument("-d",
                        "--debug",
                        dest="debug",
                        action="store_true",
                        help='enables debug output')

    parser.add_argument("-j",
                        "--json",
                        dest="json",
                        action="store_true",
                        help='to enable JSON Event')

    parser.add_argument("-k",
                        "--keepalive",
                        dest="keepalive",
                        default="0",
                        help='Keepalive timeout')

    parser.add_argument("-i",
                        "--id",
                        dest="id",
                        action="store_true",
                        help='to generate identifiers')

    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.json:
        if args.id:
            chosen_event = JSONIdEvent
        else:
            chosen_event = JSONEvent
    else:
        if args.id:
            chosen_event = StringIdEvent
        else:
            chosen_event = StringEvent

    try:
        args.keepalive = int(args.keepalive)
    except ValueError:
        log.error("keepalive takes a numerical value")
        sys.exit(1)

    ###
    try:
        application = tornado.web.Application([
            (r"/(.*)/(.*)", EventSourceHandler, dict(event_class=chosen_event,keepalive=args.keepalive)),
        ])

        if args.ssl_certfile != '' or args.ssl_keyfile != '':
            if os.path.exists(args.ssl_certfile) and os.path.exists(args.ssl_keyfile):
                application = tornado.httpserver.HTTPServer(application, ssl_options={
                    "certfile": args.ssl_certfile,
                    "keyfile": args.ssl_keyfile,
                })
            else:
                log.error("[-C|--certfile] and [-K|--keyfile] shall be specified *together* to enable SSL use. SSL is disabled.")

        application.listen(int(args.port))
        tornado.ioloop.IOLoop.instance().start()
    except ValueError:
        log.error("The port '%d' shall be a numerical value." % (args.port,))
        sys.exit(1)

    ###

if __name__ == "__main__":
    start()

