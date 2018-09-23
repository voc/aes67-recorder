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

parser.add_argument('-i', '--ini-file', action='store',
                    help="Load a custom config.ini-File")

parser.add_argument('-s', '--source-url', action='store',
                    help="RTSP Source-Url")

parser.add_argument('-d', '--destination-folder', action='store',
                    help="Destination Folder")


def parse():
    global parser

    return parser.parse_args()
