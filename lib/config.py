import logging
import os.path
from configparser import SafeConfigParser


class VocConfigParser(SafeConfigParser):
    def getlist(self, section, option):
        option = self.get(section, option).strip()
        if len(option) == 0:
            return []

        unfiltered = [x.strip() for x in option.split(',')]
        return list(filter(None, unfiltered))


def load(args):
    """
    :type args namespace
    :return VocConfigParser
    """
    files = [
        '/etc/aes67-backup.ini',
        os.path.expanduser('~/.aes67-backup.ini'),
    ]

    if args.ini_file is not None:
        files.append(args.ini_file)

    config = VocConfigParser()
    readfiles = config.read(files)

    log = logging.getLogger('ConfigParser')
    log.debug('considered config-files: \n%s',
              "\n".join([
                  "\t\t" + os.path.normpath(file)
                  for file in files
              ]))
    log.debug('successfully parsed config-files: \n%s',
              "\n".join([
                  "\t\t" + os.path.normpath(file)
                  for file in readfiles
              ]))

    if args.ini_file is not None and args.ini_file not in readfiles:
        raise RuntimeError('explicitly requested config-file "{}" '
                           'could not be read'.format(args.ini_file))

    return config
