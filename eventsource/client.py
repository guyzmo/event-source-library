import sys
import time
import argparse
import logging
log = logging.getLogger('eventsource.client')

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

class Event(object):
    """
    Defines a received event
    """
    def __init__(self):
        self.name = None
        self.data = None
        self.id = None

    def __repr__(self):
        return "Event<%s,%s,%s>" % (str(self.id), str(self.name), str(self.data.replace('\n','\\n')))

class EventSourceClient(object):
    def __init__(self,url,action,target,callback=None,retry=-1):
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
        if self.retry_timeout == 0:
            self.http_client.fetch(self.http_request, self.handle_request)
            IOLoop.instance().start()
        while self.retry_timeout!=0:
            self.http_client.fetch(self.http_request, self.handle_request)
            IOLoop.instance().start()
            time.sleep(self.retry_timeout/1000)

    def end(self):
        self.retry_timeout=0
        IOLoop.instance().stop()
    
    def handle_stream(self,message):
        event = Event()
        for line in message.strip('\r\n').split('\r\n'):
            (field, value) = line.split(":",1)
            if field == 'event':
                event.name = value
            elif field == 'data':
                value = value.lstrip()
                if event.data is None:
                    event.data = value
                else:
                    event.data = "%s\n%s" % (event.data, value)
            elif field == 'id':
                event.id = value
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
        if response.error:
            log.error(response.error)
        else:
            log.info("disconnection requested")
            self.retry_timeout=0
        IOLoop.instance().stop()

def start():
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

