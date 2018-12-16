import json
import logging
import socket
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
from gi.repository import GObject


class Watchdog(object):
    def __init__(self, config):
        self.config = config
        self.log = logging.getLogger("Watchdog")

        num_sources = len(config['sources'])
        self.last_ping = datetime.utcnow()
        GObject.timeout_add(config['watchdog']['check_interval_ms'], self.check_status)

        self.mqtt = None
        if config['watchdog']['mqtt']['enabled']:
            self.init_mqtt()

    def init_mqtt(self):
        self.mqtt = mqtt.Client()
        self.mqtt.connect(
            self.config['watchdog']['mqtt']['host'],
            self.config['watchdog']['mqtt']['port'],
            keepalive=60, bind_address="")

        if self.config['watchdog']['mqtt']['username'] and self.config['watchdog']['mqtt']['password']:
            self.mqtt.username_pw_set(
                self.config['watchdog']['mqtt']['username'],
                self.config['watchdog']['mqtt']['password'])

        self.mqtt.loop_start()

    def ping(self, src_idx):
        self.log.debug("Got Ping")
        self.last_ping = datetime.utcnow()

    def check_status(self):
        now = datetime.utcnow()
        d = (now - self.last_ping)
        milisconds = int((d.seconds * 1000) + (d.microseconds / 1000))
        if milisconds > self.config['watchdog']['warn_after_missing_signal_for_ms']:
            self.report(
                "warn",
                "No Data received within {} ms".format(milisconds))

        if milisconds > self.config['watchdog']['restart_after_missing_signal_for_ms']:
            self.report(
                "error",
                "No Data received within {} ms, restarting recorder".format(milisconds))
            sys.exit(42)

        return True

    def report(self, level, message):
        if level == 'warn':
            self.log.warn(message)
        else:
            self.log.error(message)

        if (self.mqtt):
            self.mqtt.publish("/voc/alert", json.dumps({
                "level": level,
                "msg": message,
                "component": socket.getfqdn() + ':aes67-recorder'
            }))
