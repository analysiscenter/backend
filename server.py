import sys
import json
import logging
import logging.config
import argparse

from flask import Flask
from flask_socketio import SocketIO


def create_demo_namespace(args):
    from demo.api import API_Namespace
    return API_Namespace("/api")


def create_annotation_namespace(args):
    from annotation.api import API_Namespace
    return API_Namespace(args.watch_dir, args.submitted_annotation_path, args.annotation_list_path, "/api")


def parse_args():
    parser = argparse.ArgumentParser(description="A backend for an ECG/CT demo and an ECG annotation tool.")
    subparsers = parser.add_subparsers(dest="launch_mode")
    subparsers.required = True

    parser_demo = subparsers.add_parser("demo", help="Launch an ECG/CT demo")
    parser_demo.set_defaults(func=create_demo_namespace)

    parser_annotation = subparsers.add_parser("annotation", help="Launch an ECG annotation tool")
    parser_annotation.add_argument("watch_dir", help="A path to a directory to watch for new ECG files")
    parser_annotation.add_argument("submitted_annotation_path",
                                   help="A path to a feather file with submitted ECG annotations")
    parser_annotation.add_argument("annotation_list_path",
                                   help="A path to a json file with a list of possible ECG annotations")
    parser_annotation.set_defaults(func=create_annotation_namespace)

    args = parser.parse_args()
    return args


def create_logger(args):
    with open("logger_config.json", encoding="utf-8") as json_data:
        logger_config = json.load(json_data)
    logging.config.dictConfig(logger_config)
    logger = logging.getLogger("server")
    return logger


def create_namespace(args):
    namespace = args.func(args)
    return namespace


def main():
    args = parse_args()
    logger = create_logger(args)
    namespace = create_namespace(args)

    app = Flask(__name__)
    socketio = SocketIO(app)
    socketio.on_namespace(namespace)

    logger.info("Run app")
    socketio.run(app, port=9090)


if __name__ == "__main__":
    main()
