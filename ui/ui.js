$(function() {
	var ws = new WebSocket("ws://" + location.hostname + ":9998/");
	var system_config = null;

	ws.onmessage = function(event) {
		var message = JSON.parse(event.data);
		switch (message.type) {
			case 'system_config':
				system_config = message;
				console.info('system_config', system_config);
				reset_ui();
				break;

			case 'new_filepath':
				update_filepath(message);
				break;

			case 'audio_level':
				update_audio_levels(message);
				break;

			case 'system_health_report':
				update_system_health(message);
				break;

			default:
				console.warn('unimplemented message type: ' + message.type);
		}
	};

	var $level_meters = $('.level-meters'),
		$level_meter = $level_meters.find('> .level-meter').first().remove(),
		$decay_meteters = [],
		$rms_meteters = [],
		$peak_meteters = [];

	var
		$filename_list = $('.filename-list'),
		$filename_item = $filename_list.find('> li').first().remove(),
		$filename_items = [];

	function reset_ui() {
		var num_channels = 0, channel;
		system_config.sources.forEach(function(source) {
			num_channels += source.channels;
		});

		$level_meters.empty();
		for (channel = 0; channel < num_channels; channel++) {
			$level_meter.clone().appendTo($level_meters).find('> .label').text(channel + 1);
		}

		$decay_meteters = $level_meters.find('> .level-meter > .bar.decay');
		$rms_meteters = $level_meters.find('> .level-meter > .bar.rms');
		$peak_meteters = $level_meters.find('> .level-meter > .bar.peak');

		$filename_list.empty();
		for (channel = 0; channel < num_channels; channel++) {
			$filename_item.clone().appendTo($filename_list).find('> span').text(channel + 1);
		}

		$filename_items = $filename_list.find('> li');
	}

	function update_audio_levels(message) {
		if ($rms_meteters.length === 0) {
			return;
		}

		var num_channels = message.to_channel - message.from_channel;
		for (var channel_index = 0; channel_index <= num_channels; channel_index++) {
			var global_channel_index = message.from_channel + channel_index;

			var
				decay = message.decay[channel_index],
				decay_normalized = (normalize_db(decay) * 100),
				rms = message.rms[channel_index],
				rms_normalized = (normalize_db(rms) * 100),
				peak = message.peak[channel_index],
				peak_normalized = (normalize_db(peak) * 100);

			$($decay_meteters[global_channel_index]).css('height', decay_normalized + '%');
			$($rms_meteters[global_channel_index]).css('height', rms_normalized + '%');
			$($peak_meteters[global_channel_index]).css('bottom', peak_normalized + '%');
		}
	}

	function update_filepath(message) {
		// @formatter:off
		$($filename_items[message.channel_index])
			.find("> code")
				.text(message.filepath)
		// @formatter:on
	}

	function normalize_db(db) {
		/*
		 -60db -> 1.00 (very quiet)
		 -30db -> 0.75
		 -15db -> 0.50
		  -5db -> 0.25
		  -0db -> 0.00 (very loud)
		*/
		var logscale = 1 - log10(-0.15 * db + 1);
		return clamp(logscale);
	}

	function log10(x) {
		return Math.log(x) * Math.LOG10E;
	}

	function clamp(value, min_value, max_value) {
		min_value = min_value || 0;
		max_value = max_value || 1;
		return Math.max(Math.min(value, max_value), min_value)
	}

	var
		$system_health = $('.system-health'),
		$interfaces_list = $('.interfaces-list'),
		$interface_item = $interfaces_list.find('> li').first().remove();

	function update_system_health(message) {
		// @formatter:off
		$system_health
			.find('.bytes_used')
				.text(format_bytes(message.bytes_used))
			.end()
			.find('.bytes_total')
				.text(format_bytes(message.bytes_total))
			.end()
			.find('.bytes_used_percent')
				.text(format_percent(1 - message.bytes_available_percent))
			.end()
			.find('.inodes_used')
				.text(format_inodes(message.inodes_used))
			.end()
			.find('.inodes_total')
				.text(format_inodes(message.inodes_total))
			.end()
			.find('.inodes_used_percent')
				.text(format_percent(1 - message.inodes_available_percent))
			.end();
		// @formatter:on

		$interfaces_list.empty();
		for (var interface_name in message.interfaces) {
			var interface_stats = message.interfaces[interface_name];
			// @formatter:off
			$interface_item.clone()
				.find('.name')
					.text(interface_name)
				.end()
				.find('.rx_bytes')
					.text(format_bits_per_second(interface_stats['rx']['bytes_per_second'] * 8))
				.end()
				.find('.tx_bytes')
					.text(format_bits_per_second(interface_stats['tx']['bytes_per_second'] * 8))
				.end()
				.find('.rx_packets')
					.text(format_packets_per_second(interface_stats['rx']['packets_per_second']))
				.end()
				.find('.tx_packets')
					.text(format_packets_per_second(interface_stats['tx']['packets_per_second']))
				.end()
				.appendTo($interfaces_list);
		// @formatter:on
		}
	}

	function format_percent(percent) {
		return (Math.round(percent * 100 * 100) / 100) + '%';
	}

	function format_bytes(bytes) {
		return format_number(bytes, 'Bytes', 'Byte', 'Bytes', 'B');
	}

	function format_inodes(inodes) {
		return format_number(inodes, '', '', '', '');
	}

	function format_bits_per_second(bits) {
		return format_number(bits, 'Bits/s', 'Bit/s', 'Bit/s', 'Bit/s');
	}

	function format_packets_per_second(packets) {
		return format_number(packets, 'Packets/s', 'Packet/s', 'Packets/s', 'Packets/s');
	}

	// https://stackoverflow.com/a/18650828
	function format_number(bytes, suffix_zero, suffix_singular, suffix_tens, suffix_plural, decimals) {
		if (bytes === 0) return '0 ' + suffix_zero;
		if (bytes === 1) return '1 ' + suffix_singular;
		var k = 1024,
			dm = decimals <= 0 ? 0 : decimals || 2,
			sizes = [suffix_tens, 'K' + suffix_plural, 'M' + suffix_plural, 'G' + suffix_plural, 'T' + suffix_plural, 'P' + suffix_plural, 'E' + suffix_plural, 'Z' + suffix_plural, 'Y' + suffix_plural],
			i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
	}
});
