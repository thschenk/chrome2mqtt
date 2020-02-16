#!/usr/bin/python3
"""
    Program that handles chromecast integration to mqtt.

    Copyright 2018: Thomas Bowman Morch
"""
from os import path
from datetime import datetime
import sys
import logging.config
import logging
import socket
import atexit
import signal
import json

from chrome2mqtt.mqtt import MQTT
from chrome2mqtt.devicecoordinator import DeviceCoordinator

__version__ = __VERSION__ = "1.0.0"

def parse_args(argv=None):
    #pylint: disable=line-too-long
    ''' Command line argument parser '''
    import argparse
    parser = argparse.ArgumentParser(prog='chrome2mqtt',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='chrome2mqtt\n\nConnects your chromecasts to your mqtt-broker',
                                     epilog='See more on https://github.com/tbowmo/chrome2mqtt/README.md'
                                     )
    required_flags = parser.add_mutually_exclusive_group(required=True)
    required_flags.add_argument('-max', '--MAX', action="store", type=int, default=None, help="Max number of chromecasts to expect")
    parser.add_argument('--mqttport', action="store", default=1883, type=int, help="MQTT port on host")
    parser.add_argument('--mqttclient', action="store", default=socket.gethostname(), help="Client name for mqtt")
    parser.add_argument('--mqttroot', action="store", default="chromecast", help="MQTT root topic")
    parser.add_argument('--mqttuser', action="store", default=None, help="MQTT user (if authentication is enabled for your broker)")
    parser.add_argument('--mqttpass', action="store", default=None, help="MQTT password (if authentication is enabled for your broker)")
    parser.add_argument('-H', '--mqtthost', action="store", default="127.0.0.1", help="MQTT Host")
    parser.add_argument('-l', '--logfile', action="store", default=None, help="Log to filename")
    parser.add_argument('-d', '--debug', action="store_const", dest="log", const=logging.DEBUG, help="loglevel debug")
    parser.add_argument('-v', '--verbose', action="store_const", dest="log", const=logging.INFO, help="loglevel info")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s {version}'.format(version=__VERSION__))
    parser.add_argument('-C', '--cleanup', action="store_true", dest="cleanup", help="Cleanup mqtt topic on exit")
    parser.add_argument('-S', '--standalone', action="store_true", dest="split", help="Split into separate devices")
    return parser.parse_args(argv)

def start_banner(args):
    ''' Print banner message for the programme '''
    print('Chromecast2MQTT by tbowmo')
    print('Connecting to mqtt host ' + args.mqtthost + ' port ' + str(args.mqttport))
    print('Using mqtt root ' + args.mqttroot)

def setup_logging(
        file=None,
        level=logging.WARNING
    ):
    ''' Initialize logging '''
    if path.isfile('./logsetup.json'):
        with open('./logsetup.json', 'rt') as options_file:
            config = json.load(options_file)
        logging.config.dictConfig(config)
    elif file is not None:
        logging.basicConfig(level=level,
                            filename=file,
                            format='%(asctime)s %(name)-16s %(levelname)-8s %(message)s')
    else:
        logging.basicConfig(level=level,
                            format='%(asctime)s %(name)-16s %(levelname)-8s %(message)s')

def main_loop():
    """Main operating loop, discovers chromecasts, and run forever until ctrl-c is received"""

    assert sys.version_info >= (3, 6), "You need at least python 3.6 to run this program"

    args = parse_args()
    start_banner(args)

    setup_logging(args.logfile, args.log)

    if args.MAX == 0:
        print('WARNING! max casters is set to 0, which means the script will never stop listening for new casters') #pylint: disable=line-too-long
        print('specify --max= to set the maximum number of chromecasts to expect')

    try:
        mqtt = MQTT(
            host=args.mqtthost,
            port=args.mqttport,
            client=args.mqttclient,
            root=args.mqttroot,
            user=args.mqttuser,
            password=args.mqttpass
            )
    except ConnectionError as exception:
        print('Error connecting to mqtt host {0} on port {1}'.format(args.mqtthost, args.mqttport))
        print(exception)
        sys.exit(1)

    mqtt.publish('debug/start', datetime.now().strftime('%c'), retain=True)

    coordinator = DeviceCoordinator(mqtt, args.split)

    def last_will():
        """Send a last will to the mqtt server"""
        mqtt.publish('debug/stop', datetime.now().strftime('%c'), retain=True)
        if args.cleanup:
            coordinator.cleanup()

    atexit.register(last_will)

    def signal_handler(sig, frame): #pylint: disable=unused-argument
        print('Shutting down')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    while True:
        coordinator.discover(args.MAX)
        signal.pause()
