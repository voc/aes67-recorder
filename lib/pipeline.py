import logging


class Pipeline(object):
    def __init__(self, config):
        """
        :type config lib.config.VocConfigParser
        """
        self.config = config

        self.log = logging.getLogger('Pipeline')
        self.pipeline = """
            rtspsrc location={location} !
                rtpjitterbuffer latency={latency} !
                rtpL24depay !
                audio/x-raw, channels={channels}, format={source-format}, rate={rate} !
                audioconvert !
                audio/x-raw, channels={channels}, format={capture-format}, rate={rate} !
                level name=lvl !
                deinterleave name=d
        """
