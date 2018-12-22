import json
import logging
import os
import sys
import time

from gi.repository import Gst

from lib.sources import Source
from lib.watchdog import Watchdog

DISCARD_CHANNEL_KEYWORD = "!discard"


class Pipeline(object):

    def __init__(self, config, statusServer):
        """
        :param statusServer: lib.status_server.StatusServer
        :type config lib.config.VocConfigParser
        """
        self.config = config
        self.statusServer = statusServer

        self.log = logging.getLogger('Pipeline')
        pipeline = ""

        sources = config['sources']

        self.last_seen_pts = None

        dirnames = list(self.config['channelmap'].values())
        non_unique = set(x for x in dirnames if dirnames.count(x) > 1 and x != DISCARD_CHANNEL_KEYWORD)
        if len(non_unique) > 0:
            self.log.error("Multiple channels use the same Recording-Name: " + ', '.join(non_unique))
            self.log.error("Invalid config - Quitting")
            sys.exit(42)

        self.log.debug('Constructing Pipeline-Description')
        for idx, source in enumerate(sources):
            pipeline += self.build_source_pipeline(idx, Source.from_config(config, source)) + "\n"

        # parse pipeline
        self.log.debug('Creating Pipeline:\n%s', pipeline)
        self.pipeline = Gst.parse_launch(pipeline)

        if config['clocking']['source'] == 'ptp':
            from gi.repository import GstNet
            ptp_domain = config['clocking']['ptp_domain']
            ptp_interfaces = config['clocking']['ptp_interfaces']

            self.log.info('initializing PTP-Subsystem for Network-Interface(s) %s', ptp_interfaces)
            success = GstNet.ptp_init(GstNet.PTP_CLOCK_ID_NONE, ptp_interfaces)
            if success:
                self.log.debug('successfully initializing PTP-Subsystem')
            else:
                self.log.error('failed to initializing PTP-Subsystem')
                sys.exit(42)

            self.log.debug('obtaining PTP-Clock for domain %u', ptp_domain)
            ptp_clock = GstNet.PtpClock.new('PTP-Master', ptp_domain)
            if ptp_clock != None:
                self.log.debug('obtained PTP-Clock for domain %u', ptp_domain)
            else:
                self.log.error('failed to obtain PTP-Clock')
                sys.exit(42)

            self.log.debug('waiting for PTP-Clock to sync')
            ptp_clock.wait_for_sync(Gst.CLOCK_TIME_NONE)
            self.log.info('successfully synced PTP-Clock')

            self.pipeline.use_clock(ptp_clock)

        self.log.debug('Caclulating Channel-Offsets')
        channel_offset = 0
        self.channel_offsets = {}
        for idx, source in enumerate(sources):
            last_channel = channel_offset + source['channels'] - 1
            self.log.debug('Source %d provides channels %d to %d', idx, channel_offset, last_channel)
            self.channel_offsets[idx] = (channel_offset, last_channel)
            channel_offset += source['channels']

        self.log.debug('Configuring Pipelines')
        for idx, source in enumerate(sources):
            self.configure_source_pipeline(idx, Source.from_config(config, source))

        self.log.debug('Binding Handoff-Signal')
        self.pipeline.get_by_name('sig').connect('handoff', self.on_handoff)

        # configure bus
        self.log.debug('Binding Bus-Signals')
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()

        # connect bus-message-handler for error-messages
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)

        # connect bus-message-handler for level-messages
        bus.connect("message::element", self.on_message)

        if config['watchdog']['enabled']:
            self.log.info('Starting Watchdog')
            self.watchdog = Watchdog(config)

    def build_source_pipeline(self, idx, source):
        channels = source.source_config['channels']

        pipeline = source.build_pipeline().rstrip() + """ !
            audioconvert !
            {handoff}
            audio/x-raw, channels={channels}, format={capture_format}, rate={rate} !
            tee name=tee_src_{idx}

            tee_src_{idx}. ! audioconvert ! audio/x-raw, format=S16LE ! level interval={level_interval} name=lvl_src_{idx}
            tee_src_{idx}. ! deinterleave name=d_src_{idx}
        """.format(
            idx=idx,
            channels=channels,
            handoff="identity signal-handoffs=true name=sig !" if idx == 0 else "",
            rate=self.config['source']['rate'],
            capture_format=self.config['capture']['format'],
            level_interval=self.config['status_server']['level_interval_ms'] * 1000000
        )

        for channel in range(0, channels):
            dirname = self.config['channelmap'].get(str(channel))

            if dirname == DISCARD_CHANNEL_KEYWORD:
                continue

            pipeline += """
                d_src_{idx}.src_{channel} ! splitmuxsink name=mux_src_{idx}_ch_{channel} muxer=wavenc location=/dev/null
            """.rstrip().format(
                idx=idx,
                channel=channel
            )

        return pipeline

    def configure_source_pipeline(self, source_idx, source):
        channels = source.source_config['channels']
        channel_offset, last_channel = self.channel_offsets[source_idx]

        self.log.debug('configuring channels %d to %d', channel_offset, last_channel)
        for source_channel in range(0, channels):
            channel = channel_offset + source_channel
            dirname = self.config['channelmap'].get(channel)

            if dirname == DISCARD_CHANNEL_KEYWORD:
                continue

            if dirname is None:
                dirname = "unknown/{channel}".format(channel=channel)
                self.log.warn("Channel {channel} has no mapping in the config and will be recorded as {dirname}"
                              .format(channel=channel, dirname=dirname))

            dirpath = os.path.join(self.config['capture']['folder'], dirname)
            os.makedirs(dirpath, exist_ok=True)

            el = self.pipeline.get_by_name(
                "mux_src_{source}_ch_{channel}".format(source=source_idx, channel=source_channel))
            el.connect('format-location', self.on_format_location, channel, dirpath)

    def start(self):
        # start process
        self.log.debug('Launching Mixing-Pipeline')
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_format_location(self, mux, fragment, channel, dirpath):
        filename = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + ".wav"
        filepath = os.path.join(dirpath, filename)
        self.log.info("constructing filepath for channel {channel}: {filepath}".format(
            channel=channel, filepath=filepath))
        self.send_filepath_message(channel, filepath)
        return filepath

    # this method will be called from the streaming-thread and can interact with all elements in sync
    def on_handoff(self, element, buffer):
        segment_length = self.config['capture']['segment_length_s'] * 1000000000

        if self.last_seen_pts == None:
            self.last_seen_pts = buffer.pts
            return

        if buffer.pts - self.last_seen_pts > segment_length:
            self.last_seen_pts = buffer.pts
            self.log.info('splitting segments')

            for source_idx, source in enumerate(self.config['sources']):
                channels = source['channels']
                for source_channel in range(0, channels):
                    el = self.pipeline.get_by_name(
                        "mux_src_{source}_ch_{channel}".format(source=source_idx, channel=source_channel))
                    el.emit('split-now')

    def on_message(self, bus, msg):
        if not msg.src.name.startswith('lvl_'):
            return

        if msg.type != Gst.MessageType.ELEMENT:
            return

        src_idx = int(msg.src.name[len("lvl_src_"):])
        rms = msg.get_structure().get_value('rms')
        peak = msg.get_structure().get_value('peak')
        decay = msg.get_structure().get_value('decay')
        self.log.debug('level_callback src #%u\n  rms=%s\n  peak=%s\n  decay=%s', src_idx, rms, peak, decay)
        self.send_level_message(src_idx, rms, peak, decay)
        self.watchdog.ping(src_idx)

    def on_eos(self, bus, message):
        self.log.debug('Received End-of-Stream-Signal on Mixing-Pipeline')

    def on_error(self, bus, message):
        self.log.debug('Received Error-Signal on Mixing-Pipeline')
        (error, debug) = message.parse_error()
        self.log.debug('Error-Details: #%u: %s', error.code, debug)

    def send_level_message(self, src_idx, rms, peak, decay):
        from_channel, to_channel = self.channel_offsets[src_idx]
        message = json.dumps({
            "type": "audio_level",
            "source_index": src_idx,
            "from_channel": from_channel,
            "to_channel": to_channel,
            "rms": rms,
            "peak": peak,
            "decay": decay,
        })
        self.statusServer.transmit(message)

    def send_filepath_message(self, channel, filepath):
        message = json.dumps({
            "type": "new_filepath",
            "channel_index": channel,
            "filepath": filepath,
        })
        self.statusServer.transmit(message)
