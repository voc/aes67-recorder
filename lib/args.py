import argparse

parser = argparse.ArgumentParser('AES64 Backup')

parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="Also print INFO and DEBUG messages.")

parser.add_argument('-c', '--color',
                    action='store',
                    choices=['auto', 'always', 'never'],
                    default='auto',
                    help="Control the use of colors in the Log-Output")

parser.add_argument('-t', '--timestamp', action='store_true',
                    help="Enable timestamps in the Log-Output")

parser.add_argument('-i', '--config-file', action='store', required=True,
                    help="Path to a specific Config-Yaml-File to load")

parser.add_argument('-s', '--source-url', action='store',
                    help="RTSP Source-Url")

parser.add_argument('-f', '--capture-folder', action='store',
                    help="Destination Folder")

parser.add_argument('--demo', action='store_true',
                    help="Enable Demo-Mode, where instead of a real RTSP-Source a internally generated test-source is used")


def parse():
    global parser

    return parser.parse_args()
