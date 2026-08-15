import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';

class LiveSpeechService {
  final SpeechToText _speech = SpeechToText();
  bool _ready = false;

  bool get isListening => _speech.isListening;

  Future<void> listen({
    required String language,
    required void Function(String text) onText,
  }) async {
    _ready = _ready || await _speech.initialize();
    if (!_ready) throw StateError('Speech recognition is unavailable on this device.');
    await _speech.listen(
      onResult: (result) => onText(result.recognizedWords),
      listenOptions: SpeechListenOptions(
        localeId: language == 'ur' ? 'ur_PK' : 'en_PK',
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 4),
        partialResults: true,
      ),
    );
  }

  Future<void> stop() => _speech.stop();
}

class TtsService {
  final FlutterTts _tts = FlutterTts();

  Future<void> speak(String text, String language) async {
    await _tts.stop();
    await _tts.setLanguage(language == 'ur' ? 'ur-PK' : 'en-PK');
    await _tts.setSpeechRate(0.45);
    await _tts.speak(text);
  }

  Future<void> pause() => _tts.pause();
  Future<void> stop() => _tts.stop();
}
