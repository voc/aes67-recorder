$(function() {
	var ws = new WebSocket("ws://127.0.0.1:9998/");
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
				break;

			case 'audio_level':
				set_audio_level(message);
				break;

			case 'system_health_report':
				break;

			default:
				console.warn('unimplemented message type: ' + message.type);
		}
	};

	var $container = $('.level-meters'),
		$level_meter = $container.find('> .level-meter').first().remove(),
		$decay_meteters = [],
		$rms_meteters = [],
		$peak_meteters = [];

	function reset_ui() {
		var num_channels = 0;
		system_config.sources.forEach(function(source) {
			num_channels += source.channels;
		});

		$container.empty();
		for (var channel = 0; channel < num_channels; channel++) {
			$level_meter.clone().appendTo($container).find('> .label').text(channel + 1);
		}

		$decay_meteters = $container.find('> .level-meter > .bar.decay');
		$rms_meteters = $container.find('> .level-meter > .bar.rms');
		$peak_meteters = $container.find('> .level-meter > .bar.peak');
	}

	function set_audio_level(message) {
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
});
