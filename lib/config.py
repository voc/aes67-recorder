import logging
import os.path
from pprint import pformat

import yaml

log = logging.getLogger('Config')


def load(args):
    config = _load(args)

    if args.demo:
        config['sources'] = [{
            "type": "demo",
            "channels": 8
        }]

    log.debug('Loaded config: \n%s', pformat(config))

    return config


def _load(args):
    if args.config_file is not None:
        log.info("Loading specified Config-File %s", args.config_file)
        with open(args.config_file, 'r') as f:
            return yaml.safe_load(f)

    else:
        files = [
            '/etc/aes67-backup.yaml',
            os.path.expanduser('~/.aes67-backup.yaml'),
        ]
        for file in files:
            try:
                log.info("Trying to load Config-File %s", file)
                with open(file, 'r') as f:
                    return yaml.safe_load(f)
            except:
                pass

    log.info("No Config-File found")
    raise RuntimeError('no config-file found or specified')
