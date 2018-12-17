#!/usr/bin/env python3
import asyncio
import json
import logging

import websockets
from aiohttp import web

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("webgui")

websocket_clients = set()
loop = asyncio.get_event_loop()

system_config = None


async def handle_websocket_connection(websocket, path):
    global system_config
    log = logging.getLogger("websocket")

    log.info("new websocket-client, repeating system_config")
    await websocket.send(system_config)

    websocket_clients.add(websocket)
    log.info("now %u websocket-clients" % len(websocket_clients))

    try:
        while True:
            message = await websocket.recv()
            log.debug("received from websocket: %s" % message)
    except:
        websocket_clients.remove(websocket)
        log.info("now %u websocket-clients" % len(websocket_clients))


async def read_from_tcp(host, port):
    global system_config
    log = logging.getLogger("tcp-server")

    reader, writer = await asyncio.open_connection(host, port)

    log.info("connected")
    while not reader.at_eof():
        bytes = await reader.readline()
        if len(bytes) == 0:
            break

        line = bytes.decode('utf-8').rstrip()
        message = json.loads(line)
        if message['type'] == 'system_config':
            log.info("received system_config: %s" % line)
            system_config = line

        log.debug('Received: %s' % line)
        if websocket_clients:
            await asyncio.wait([client.send(line) for client in websocket_clients])

    log.info("disconnected, stopping mainloop")
    writer.close()
    loop.stop()


def handle_index(request):
    with open('ui/index.html', 'r') as f:
        return web.Response(text=f.read(), content_type="text/html", charset="utf-8")


app = web.Application()
app.router.add_get("/", handle_index)
app.router.add_static("/ui", "ui", show_index=True)

webserver = loop.create_server(app.make_handler(), '0.0.0.0', 8080)

log.info("Starting Webserver on port 8080")
loop.run_until_complete(webserver)

log.info("Starting Websocket-Server on port 9998")
loop.run_until_complete(websockets.serve(
    handle_websocket_connection, '0.0.0.0', 9998))

log.info("Starting TCP-Client on port 9999")
loop.run_until_complete(read_from_tcp('127.0.0.1', 9999))

loop.run_forever()
log.info("Bye")
