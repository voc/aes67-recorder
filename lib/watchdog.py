import logging
import sys
from datetime import datetime

from gi.repository import GObject


class Watchdog(object):
    def __init__(self, config):
        self.config = config
        self.log = logging.getLogger("Watchdog")

        num_sources = len(config['sources'])
        now = datetime.utcnow()
        self.log.info("Expecting regular pings from %u sources", num_sources)
        self.last_ping = {idx: now for idx in range(0, num_sources)}

        GObject.timeout_add(config['watchdog']['check_interval_ms'], self.check_status)

    def ping(self, src_idx):
        self.log.info("Got Ping from source %u", src_idx)
        self.last_ping[src_idx] = datetime.utcnow()

    def check_status(self):
        now = datetime.utcnow()
        for src_idx, last_ping in self.last_ping.items():
            d = (now - last_ping)
            milisconds = int((d.seconds * 1000) + (d.microseconds / 1000))
            if milisconds > self.config['watchdog']['warn_after_missing_signal_for_ms']:
                self.log.error("Source %d has not responded within %d ms", src_idx, milisconds)

            if milisconds > self.config['watchdog']['restart_after_missing_signal_for_ms']:
                self.log.error("Source %d has not responded within %d ms, restarting recorder", src_idx, milisconds)
                sys.exit(42)

        return True
