import sys
import argparse

import json
import urllib2

def send_json(url, data):
    if isinstance(data,str):
        data = json.dumps(json.loads(data))
    else:
        data = json.dumps(data)
    try:
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        try:
            response = f.read()
            print response
            return 0
        finally:
            f.close()
    except urllib2.HTTPError, err:
        print "Unable to send request: %s" % (err,)
        return 1

def send_string(url, data):
    try:
        f = urllib2.urlopen(url, data)
        try:
            response = f.read()
            print response
            return 0
        finally:
            f.close()
    except urllib2.HTTPError, err:
        print "Unable to send request: %s" % (err,)
        return 1
    
def start():
    parser = argparse.ArgumentParser(prog=sys.argv[0],
                            description="Generates event for Event Source Library")

    parser.add_argument("token",
                        help='Token to be used for connection')

    parser.add_argument("action",
                        help='Action to send')

    parser.add_argument("data",
                        nargs='?',
                        default="",
                        help='Data to be sent')

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

    parser.add_argument("-j",
                        "--json",
                        dest="json",
                        action="store_true",
                        help='Treat data as JSON')

    args = parser.parse_args(sys.argv[1:])

    if args.json:
        sys.exit( send_json("http://%(host)s:%(port)s/%(action)s/%(token)s" % args.__dict__, args.data) )
    else:
        sys.exit( send_string("http://%(host)s:%(port)s/%(action)s/%(token)s" % args.__dict__, args.data) )

if __name__ == "__main__":
    start()
