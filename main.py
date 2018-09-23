#!/usr/bin/env python3
import logging
import signal
import sys

import gi

# import GStreamer and GLib-Helper classes
gi.require_version('Gst', '1.0')
gi.require_version('GstNet', '1.0')
from gi.repository import Gst, GObject

# import local classes
from lib.loghandler import LogHandler
from lib.pipeline import Pipeline
import lib.args
import lib.config

# check min-version
minGst = (1, 5)
minPy = (3, 0)

Gst.init([])
if Gst.version() < minGst:
    raise Exception('GStreamer version', Gst.version(),
                    'is too old, at least', minGst, 'is required')

if sys.version_info < minPy:
    raise Exception('Python version', sys.version_info,
                    'is too old, at least', minPy, 'is required')

# init GObject & Co. before importing local classes
GObject.threads_init()


class Backuptool(object):
    def __init__(self, config):
        """
        :type config lib.config.VocConfigParser
        """
        self.config = config

        # initialize mainloop
        self.log = logging.getLogger('Main')
        self.log.debug('creating GObject-MainLoop')
        self.mainloop = GObject.MainLoop()

        # initialize subsystem
        self.log.debug('creating A/V-Pipeline')
        self.pipeline = Pipeline(config)

        # TODO clocking

    def run(self):
        self.log.info('running GObject-MainLoop')
        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            self.log.info('Terminated via Ctrl-C')

    def quit(self):
        self.log.info('quitting GObject-MainLoop')
        self.mainloop.quit()


# run mainclass
def main():
    # parse command-line args
    args = lib.args.parse()

    docolor = (args.color == 'always') \
              or (args.color == 'auto' and sys.stderr.isatty())

    handler = LogHandler(docolor, args.timestamp)
    logging.root.handlers = [handler]

    if args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.root.setLevel(level)

    # make killable by ctrl-c
    logging.debug('setting SIGINT handler')
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    logging.info('Python Version: %s', sys.version_info)
    logging.info('GStreamer Version: %s', Gst.version())

    logging.debug('loading Config')
    config = lib.config.load(args)

    # init main-class and main-loop
    logging.debug('initializing AES67-Backup')
    backup_tool = Backuptool(config)

    logging.debug('running AES67-Backup')
    backup_tool.run()


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)
