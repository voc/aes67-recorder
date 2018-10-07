from flask import render_template


class WebUI(object):
    def __init__(self, app, sio):
        @app.route('/')
        def index():
            """Serve the client-side application."""
            return render_template('index.html')

        @sio.on('connect', namespace='/chat')
        def connect(sid, environ):
            print("connect ", sid)

        @sio.on('chat message', namespace='/chat')
        def message(sid, data):
            print("message ", data)
            sio.emit('reply', room=sid)

        @sio.on('disconnect', namespace='/chat')
        def disconnect(sid):
            print('disconnect ', sid)
