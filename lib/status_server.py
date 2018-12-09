import json
import logging
import os
import socket

from gi.repository import GObject


class StatusServer(object):
    def __init__(self, config):
        self.log = logging.getLogger('Status')
        self.config = config

        self.boundSocket = None
        self.currentConnections = dict()

        port = config['status_server']['port']
        bind = config['status_server']['bind']
        self.log.debug('Binding to Source-Socket on [%s]:%u', bind, port)
        self.boundSocket = socket.socket(socket.AF_INET6)
        self.boundSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.boundSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY,
                                    False)

        self.boundSocket.bind((bind, port))
        self.boundSocket.listen(1)

        self.log.debug('Setting GObject io-watch on Socket')
        GObject.io_add_watch(self.boundSocket, GObject.IO_IN, self.on_connect)

        self.log.debug('Setting GObject io-watch on Socket')
        GObject.timeout_add(config['status_server']['disk_level_interval_ms'], self.send_disk_level)

    def on_connect(self, sock, *args):
        conn, addr = sock.accept()
        conn.setblocking(False)

        self.log.info("Incomming Connection from [%s]:%u (fd=%u)",
                      addr[0], addr[1], conn.fileno())

        self.currentConnections[conn] = conn
        self.log.info('Now %u Receiver connected', len(self.currentConnections))

        self.log.debug('setting gobject io-watch on connection')
        GObject.io_add_watch(conn, GObject.IO_IN, self.on_data)
        return True

    def on_data(self, conn, _, *args):
        try:
            while True:
                try:
                    command = conn.recv(4096).decode(errors='replace')
                    command = command.strip()

                    if command == 'quit' or command == 'exit':
                        self.log.info("Client asked us to close the Connection")
                        self.close_connection(conn)
                        return False

                except UnicodeDecodeError as e:
                    continue

        except BlockingIOError:
            pass

        return True

    def close_connection(self, conn):
        if conn in self.currentConnections:
            conn.close()
            del (self.currentConnections[conn])

        self.log.info('Now %u Receiver connected', len(self.currentConnections))

    def transmit(self, line):
        for conn in self.currentConnections:
            conn.sendall(bytes(line + "\n", "utf-8"))

    def send_disk_level(self):
        f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail = \
            os.statvfs(self.config['capture']['folder'])[0:8]
        message = json.dumps({
            "type": "disk_level",

            "bytes_total": f_blocks * f_frsize,
            "bytes_free": f_bfree * f_frsize,
            "bytes_available": f_bavail * f_frsize,
            "bytes_available_percent": f_bfree / f_blocks,

            "inodes_total": f_files,
            "inodes_free": f_ffree,
            "inodes_available": f_favail,
            "inodes_available_percent": f_favail / f_files,
        })
        self.transmit(message)
        return True
