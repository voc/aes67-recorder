import logging
from multiprocessing import Process

import eventlet
import eventlet.greenthread
import eventlet.wsgi
import socketio
from flask import Flask

from lib.webui import WebUI


class Webserver(object):
    def __init__(self, config):
        self.log = logging.getLogger("Webserver")
        self.config = config
        self._process = Process(target=self.process)

    def start(self):
        self.log.info("starting Webserver process")
        self._process.start()
        self.log.debug("Webserver process running as pid %u", self._process.pid)

    def stop(self):
        self.log.debug("killing Webserver process to terminate")

        # the only way to terminate an eventlet.wsgi.server cleanly is by raising an StopServing error from inside
        # one of its greenthreads. As this is not easy to achieve without crazy hacks, just don't try and kill the whole
        # process
        self._process.terminate()

    # run the WebUI in a deparate process so it can use GreenThreads which are required by the SocketIO Websocket
    # subsystem, while the main process is spinnging in the GObject MainLoop
    def process(self):
        sio = socketio.Server()
        app = Flask(__name__)

        webui = WebUI(app, sio)

        # wrap Flask application with engineio's middleware
        middleware = socketio.Middleware(sio, app)

        # deploy as an eventlet WSGI server
        addr = (self.config['gui']['listen'], int(self.config['gui']['port']))
        eventlet.wsgi.server(eventlet.listen(addr), middleware)
