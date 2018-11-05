import logging
import os
import time

from gi.repository import Gst

from lib.sources import Source

DISCARD_CHANNEL_KEYWORD = "!discard"


class Pipeline(object):
    def __init__(self, config):
        """
        :type config lib.config.VocConfigParser
        """
        self.config = config

        self.log = logging.getLogger('Pipeline')
        pipeline = ""

        sources = config['sources']

        self.log.debug('Constructing Pipeline-Description')
        for idx, source in enumerate(sources):
            pipeline += self.build_source_pipeline(idx, Source.from_config(config, source)) + "\n"

        # parse pipeline
        self.log.debug('Creating Pipeline:\n%s', pipeline)
        self.pipeline = Gst.parse_launch(pipeline)
        # self.pipeline.use_clock(Clock) # TODO

        self.log.debug('Configuring Pipelines')
        for idx, source in enumerate(sources):
            self.configure_source_pipeline(idx, Source.from_config(config, source))

        # configure bus
        self.log.debug('Binding Bus-Signals')
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()

        # connect bus-message-handler for error-messages
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)

        # connect bus-message-handler for level-messages
        bus.connect("message::element", self.on_level)

    def build_source_pipeline(self, idx, source):
        channels = source.source_config['channels']

        pipeline = source.build_pipeline().rstrip() + """ !
            audioconvert !
            audio/x-raw, channels={channels}, format={capture_format}, rate={rate} !
            tee name=tee_src_{idx}

            tee_src_{idx}. ! audioconvert ! audio/x-raw, format=S16LE ! level interval={level_interval} name=lvl_src_{idx}
            tee_src_{idx}. ! deinterleave name=d_src_{idx}
        """.format(
            idx=idx,
            channels=channels,
            rate=self.config['source']['rate'],
            capture_format=self.config['capture']['format'],
            level_interval=self.config['gui']['level-interval'] * 1000000
        )

        segment_length = self.config['capture']['segment-length'] * 1000000000
        for channel in range(0, channels):
            dirname = self.config['channelmap'].get(str(channel))

            if dirname == DISCARD_CHANNEL_KEYWORD:
                continue

            pipeline += """
                d_src_{idx}.src_{channel} ! splitmuxsink name=mux_src_{idx}_ch_{channel} muxer=wavenc max-size-time={segment_length} location=/tmp/aes67_{channel}_%05d.wav
            """.rstrip().format(
                idx=idx,
                channel=channel,
                segment_length=segment_length
            )

        return pipeline

    def configure_source_pipeline(self, source_idx, source):
        channels = source.source_config['channels']

        for channel in range(0, channels):
            dirname = self.config['channelmap'].get(channel)

            if dirname == DISCARD_CHANNEL_KEYWORD:
                continue

            if dirname is None:
                dirname = "unknown/{channel}".format(channel=channel)
                self.log.warn("Channel {channel} has no mapping in the config and will be recorded as {dirname}"
                              .format(channel=channel, dirname=dirname))

            dirpath = os.path.join(self.config['capture']['folder'], dirname)
            os.makedirs(dirpath, exist_ok=True)

            el = self.pipeline.get_by_name("mux_src_{source}_ch_{channel}".format(source=source_idx, channel=channel))
            el.connect('format-location', self.on_format_location, channel, dirpath)

    def start(self):
        # start process
        self.log.debug('Launching Mixing-Pipeline')
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_format_location(self, mux, fragment, channel, dirpath):
        filename = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + ".wav"
        filepath = os.path.join(dirpath, filename)
        self.log.debug("constructing filepath for channel {channel}: {filepath}".format(
            channel=channel, filepath=filepath))
        return filepath

    def on_level(self, bus, msg):
        if msg.src.name != 'lvl':
            return

        if msg.type != Gst.MessageType.ELEMENT:
            return

        rms = msg.get_structure().get_value('rms')
        peak = msg.get_structure().get_value('peak')
        decay = msg.get_structure().get_value('decay')
        self.log.debug('level_callback\n  rms=%s\n  peak=%s\n  decay=%s', rms, peak, decay)

    def on_eos(self, bus, message):
        self.log.debug('Received End-of-Stream-Signal on Mixing-Pipeline')

    def on_error(self, bus, message):
        self.log.debug('Received Error-Signal on Mixing-Pipeline')
        (error, debug) = message.parse_error()
        self.log.debug('Error-Details: #%u: %s', error.code, debug)
