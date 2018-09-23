import logging


class Pipeline(object):
    def __init__(self, config):
        """
        :type config lib.config.VocConfigParser
        """
        self.config = config

        self.log = logging.getLogger('Pipeline')
        self.pipeline = ""

        if config['source'].getboolean('demo'):
            self.pipeline += """
                audiotestsrc !
            """
        else:
            self.pipeline += """
                rtspsrc location={location} !
                    rtpjitterbuffer latency={latency} !
                    rtpL24depay !
                    audio/x-raw, channels={channels}, format={source_format}, rate={rate} !
                    audioconvert !
            """

        self.pipeline += """
                audio/x-raw, channels={channels}, format={capture_format}, rate={rate} !
                level name=lvl !
                deinterleave name=d
        """.format(
            location=config['source']['url'],
            latency=config['clocking']['jitterbuffer-seconds'],
            channels=config['source']['channels'],
            rate=config['source']['rate'],
            source_format=config['source']['format'],
            capture_format=config['capture']['format']
        )

        for channel in range(0, config['source'].getint('channels')):
            channel_filename = config['channelmap'].get(str(channel))

            if channel_filename is None:
                channel_filename = "unknown/{channel}".format(channel=channel)

                self.log.warn("Channel {channel} has no mapping in the config and will be recorded as {filename}"
                              .format(channel=channel, filename=channel_filename))

            if channel_filename == "!discard":
                continue

            # TODO create dirs

            self.pipeline += """
                d.src_{channel} ! wavenc ! filesink buffer-mode=full buffer-size={buffer_size} name=writer_{channel} location={filename}
            """.format(
                channel=channel,
                buffer_size=config['capture']['buffer-size'],
                filename=channel_filename
            ).rstrip()

        print(self.pipeline)
