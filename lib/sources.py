from abc import abstractmethod


class Source(object):
    @staticmethod
    def from_config(config, source_config):
        type = source_config['type'].lower()
        if type == 'demo':
            return DemoSource(config, source_config)
        elif type == 'rtsp':
            return RtspSource(config, source_config)
        elif type == 'udp':
            return UdpSource(config, source_config)
        else:
            raise RuntimeError("Unknown type of source: " + type)

    def __init__(self, config, source_config):
        self.config = config
        self.source_config = source_config

    @abstractmethod
    def build_pipeline(self):
        pass

    def _build_jitterbuffer(self):
        if self.config['clocking']['jitterbuffer']:
            return "rtpjitterbuffer latency={latency} !".format(latency=self.config['clocking']['jitterbuffer'])
        else:
            return ""

    def _build_sourcecaps(self):
        return "audio/x-raw, channels={channels}, format={source_format}, rate={rate}".format(
            channels=self.source_config['channels'],
            rate=self.config['source']['rate'],
            source_format=self.config['source']['format'],
        )


class DemoSource(Source):
    def build_pipeline(self):
        return """
            audiotestsrc is-live=true
        """


class RtspSource(Source):
    def build_pipeline(self):
        return """
            rtspsrc protocols=udp-mcast location={location} !
                {jitterbuffer}
                rtpL24depay !
                {sourcecaps}
        """.format(
            location=self.source_config['location'],
            jitterbuffer=self._build_jitterbuffer(),
            sourcecaps=self._build_sourcecaps(),
        )


class UdpSource(Source):
    def build_pipeline(self):
        return """
            udpsrc address={address} port={port} multicast-iface={iface} !
                application/x-rtp, clock-rate={rate}, channels={channels} !
                {jitterbuffer}
                rtpL24depay !
                {sourcecaps}
        """.format(
            address=self.source_config['address'],
            port=self.source_config['port'],
            iface=self.source_config.get('iface'),
            rate=self.config['source']['rate'],
            channels=self.source_config['channels'],
            jitterbuffer=self._build_jitterbuffer(),
            sourcecaps=self._build_sourcecaps(),
        )
