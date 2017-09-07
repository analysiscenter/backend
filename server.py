from flask import Flask
from flask_socketio import SocketIO
from api import API_Namespace


app = Flask(__name__)
#app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app)
socketio.on_namespace(API_Namespace('/api'))

if __name__ == '__main__':
    print("Run app")
    socketio.run(app, port=9090)
