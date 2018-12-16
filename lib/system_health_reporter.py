import json
import logging
import os

from gi.repository import GObject

from lib.procnetdev import ProcNetDev


class SystemHealthReporter(object):
    def __init__(self, config, statusServer):
        self.log = logging.getLogger('SystemHealthReporter')
        self.config = config
        self.statusServer = statusServer

        self.log.info('Fetching initial network status')
        self.last_net_stats = ProcNetDev(auto_update=False)

        self.log.debug('Setting Timer for System-Health-Reports')
        GObject.timeout_add(config['status_server']['system_health_report_interval_ms'], self.send_system_health)

    def send_system_health(self):
        self.log.info('Sending System-Health-Reports')
        f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail = \
            os.statvfs(self.config['capture']['folder'])[0:8]

        updated_net_stats = ProcNetDev(auto_update=False)
        last_net_stats = self.last_net_stats
        seconds = (updated_net_stats.updated - last_net_stats.updated).seconds
        if seconds < 1:
            self.log.error("System-Health re-send attempt")
            return True

        message = json.dumps({
            "type": "system_health_report",

            "bytes_total": f_blocks * f_frsize,
            "bytes_free": f_bfree * f_frsize,
            "bytes_available": f_bavail * f_frsize,
            "bytes_available_percent": f_bfree / f_blocks,

            "inodes_total": f_files,
            "inodes_free": f_ffree,
            "inodes_available": f_favail,
            "inodes_available_percent": f_favail / f_files,

            "interfaces": dict(map(
                lambda ifname: (
                    ifname,
                    self.extract_interface_data(self.last_net_stats[ifname], updated_net_stats[ifname], seconds)),
                updated_net_stats
            ))
        })
        self.last_net_stats = updated_net_stats
        self.statusServer.transmit(message)
        return True

    def extract_interface_data(self, last_net_stats, updated_net_stats, seconds):
        return {
            "rx": {
                "bytes": updated_net_stats['receive']['bytes'],
                "packets": updated_net_stats['receive']['packets'],
                "bytes_per_second": (updated_net_stats['receive']['bytes'] -
                                     last_net_stats['receive']['bytes']) / seconds,
                "packets_per_second": (updated_net_stats['receive']['packets'] -
                                       last_net_stats['receive']['packets']) / seconds
            },
            "tx": {
                "bytes": updated_net_stats['transmit']['bytes'],
                "packets": updated_net_stats['transmit']['packets'],
                "bytes_per_second": (updated_net_stats['transmit']['bytes'] -
                                     last_net_stats['transmit']['bytes']) / seconds,
                "packets_per_second": (updated_net_stats['transmit']['packets'] -
                                       last_net_stats['transmit']['packets']) / seconds
            },
        }
