.. Event Source Library documentation master file, created by
   sphinx-quickstart on Sat May 26 21:21:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Eventsource library
===================

Contents:

.. toctree::
   :maxdepth: 2

eventsource Package
===================

.. note::
this package installs also three utilities:
    - **eventsource-server** : that helps to create an eventsource server (module `eventsource.listener`)
    - **eventsource-client** : that helps to create an eventsource client (module `eventsource.client`)
    - **eventsource-request** : that helps to send requests to the client through the server (module `eventsource.request`)
see `--help` or README for more information

:mod:`listener` Module
----------------------

This module opens a new long polling connection on a listener, and waits for events to come.

.. automodule:: eventsource.listener
    :members:

:mod:`client` Module
--------------------

This module listens for incoming connections and forwards events from "request" to "client"
using tornado http long-polling on the client side, and http post on the request side.

.. automodule:: eventsource.client
    :members:
    :undoc-members:

:mod:`request` Module
---------------------

This module only connects to listener's rest POST interface to send new events

.. automodule:: eventsource.request
    :members:
    :undoc-members:

.. include:: ../README.rst

Resources
=========

    - http://stackoverflow.com/questions/10665569/websocket-event-source-implementation-to-expose-a-two-way-rpc-to-a-python-dj
    - http://stackoverflow.com/questions/8812715/using-a-simple-python-generator-as-a-co-routine-in-a-tornado-async-handler
    - http://dev.w3.org/html5/eventsource/
    - http://github.com/guyzmo/event-source-library/
    - http://www.tornadoweb.org/


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

