import logging
import socket

from gi.repository import GObject


class StatusServer(object):
    def __init__(self, config):
        self.log = logging.getLogger('StatusServer')
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

    def on_connect(self, sock, *args):
        conn, addr = sock.accept()
        conn.setblocking(False)

        self.log.info("Incomming Connection from [%s]:%u (fd=%u)",
                      addr[0], addr[1], conn.fileno())

        self.currentConnections[conn] = conn
        self.log.info('Now %u Receiver connected', len(self.currentConnections))

        self.log.debug('setting gobject io-watch on connection')
        GObject.io_add_watch(conn, GObject.IO_ERR | GObject.IO_HUP, self.on_error)
        return True

    def on_error(self, conn, condition):
        self.close_connection(conn)

    def close_connection(self, conn):
        if conn in self.currentConnections:
            conn.close()
            del (self.currentConnections[conn])

        self.log.info('Now %u Receiver connected', len(self.currentConnections))

    def transmit(self, line):
        connections = list(self.currentConnections)
        for conn in connections:
            try:
                conn.sendall(bytes(line + "\n", "utf-8"))
            except Exception:
                self.log.debug('Exception during transmit, closing connection')
                self.close_connection(conn)
