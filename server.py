import argparse

from flask import Flask
from flask_socketio import SocketIO


def create_demo_namespace(args):
    from demo.api import API_Namespace
    return API_Namespace("/api")


def create_annotation_namespace(args):
    from annotation.api import API_Namespace
    return API_Namespace(args.watch_dir, args.annotation_path, "/api")


def create_namespace():
    parser = argparse.ArgumentParser(description="A backend for an ECG/CT demo and an ECG annotation tool.")
    subparsers = parser.add_subparsers(dest="launch_mode")
    subparsers.required = True

    parser_demo = subparsers.add_parser("demo", help="Launch an ECG/CT demo")
    parser_demo.set_defaults(func=create_demo_namespace)

    parser_annotation = subparsers.add_parser("annotation", help="Launch an ECG annotation tool")
    parser_annotation.add_argument("watch_dir", help="A path to a directory to watch for new ECG files")
    parser_annotation.add_argument("annotation_path", help="A path to a file with an ECG annotation")
    parser_annotation.set_defaults(func=create_annotation_namespace)

    args = parser.parse_args()
    namespace = args.func(args)
    return namespace


def main():
    namespace = create_namespace()
    app = Flask(__name__)
    socketio = SocketIO(app)
    socketio.on_namespace(namespace)
    print("Run app")
    socketio.run(app, port=9090)


if __name__ == "__main__":
    main()
