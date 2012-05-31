"""
.. module:: listener 
:platform: Unix
:synopsis: This module provides an eventsource client based on tornado

.. moduleauthor:: Bernard Pratz <guyzmo@hackable-devices.org>

"""
import sys
import time
import argparse
import logging
log = logging.getLogger('eventsource.client')

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

class Event(object):
    """
    Contains a received event to be processed
    """
    def __init__(self):
        self.name = None
        self.data = None
        self.id = None

    def __repr__(self):
        return "Event<%s,%s,%s>" % (str(self.id), str(self.name), str(self.data.replace('\n','\\n')))

class EventSourceClient(object):
    """
    This module opens a new connection to an eventsource server, and wait for events.
    """
    def __init__(self,url,action,target,callback=None,retry=0):
        """
        Build the event source client
        :param url: string, the url to connect to
        :param action: string of the listening action to connect to
        :param target: string with the listening token
        :param callback: function with one parameter (Event) that gets called for each received event
        :param retry: timeout between two reconnections (0 means no reconnection)
        """
        log.debug("EventSourceClient(%s,%s,%s,%s,%s)" % (url,action,target,callback,retry))
        
        self._url = "http://%s/%s/%s" % (url,action,target)
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        self.http_client = AsyncHTTPClient()
        self.http_request = HTTPRequest(url=self._url,
                                        method='GET',
                                        headers={"content-type":"text/event-stream"},
                                        request_timeout=0,
                                        streaming_callback=self.handle_stream)
        if callback is None:
            self.cb = lambda e: log.info( "received %s" % (e,) )
        else:
            self.cb = callback
        self.retry_timeout = int(retry)

    def poll(self):
        """
        Function to call to start listening
        """
        log.debug("poll()")
        
        if self.retry_timeout == 0:
            self.http_client.fetch(self.http_request, self.handle_request)
            IOLoop.instance().start()
        while self.retry_timeout!=0:
            self.http_client.fetch(self.http_request, self.handle_request)
            IOLoop.instance().start()
            time.sleep(self.retry_timeout/1000)

    def end(self):
        """
        Function to call to end listening
        """
        log.debug("end()")
        
        self.retry_timeout=0
        IOLoop.instance().stop()
    
    def handle_stream(self,message):
        """
        Acts on message reception
        :param message: string of an incoming message

        parse all the fields and builds an Event object that is passed to the callback function
        """
        log.debug("handle_stream(...)")

        event = Event()
        for line in message.strip('\r\n').split('\r\n'):
            (field, value) = line.split(":",1)
            if field == 'event':
                event.name = value.lstrip()
            elif field == 'data':
                value = value.lstrip()
                if event.data is None:
                    event.data = value
                else:
                    event.data = "%s\n%s" % (event.data, value)
            elif field == 'id':
                event.id = value.lstrip()
            elif field == 'retry':
                try:
                    self.retry_timeout = int(value)
                    log.info( "timeout reset: %s" % (value,) )
                except ValueError:
                    pass
            elif field == '':
                log.info( "received comment: %s" % (value,) )
            else:
                raise Exception("Unknown field !")
        if event.name is not None:
            self.cb(event)
                

    def handle_request(self,response):
        """
        Function that gets called on non long-polling actions, 
        on error or on end of polling.

        :param response: tornado's response object that handles connection response data
        """
        log.debug("handle_request(response=%s)" % (response,))
        
        if response.error:
            log.error(response.error)
        else:
            log.info("disconnection requested")
            self.retry_timeout=0
        IOLoop.instance().stop()

def start():
    """helper method to create a commandline utility"""
    parser = argparse.ArgumentParser(prog=sys.argv[0],
                            description="Event Source Client")
    parser.add_argument("-H",
                        "--host",
                        dest="host",
                        default='127.0.0.1',
                        help='Host to connect to')
    # PORT ARGUMENT
    parser.add_argument("-P",
                        "--port",
                        dest="port",
                        default='8888',
                        help='Port to be used connection')

    parser.add_argument("-d",
                        "--debug",
                        dest="debug",
                        action="store_true",
                        help='enables debug output')

    parser.add_argument("-r",
                        "--retry",
                        dest="retry",
                        default='-1',
                        help='Reconnection timeout')

    parser.add_argument(dest="token",
                        help='Token to be used for connection')

    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ###

    def log_events(event):
        log.info( "received %s" % (event,) )

    EventSourceClient(url="%(host)s:%(port)s" % args.__dict__,
                      action="poll",
                      target=args.token,
                      retry=args.retry).poll()

    ###
    

if __name__ == "__main__":
    start()

