import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../../core/errors/app_exception.dart';
import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key, this.sessionId, this.relatedScanId});

  final String? sessionId;
  final String? relatedScanId;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _message = TextEditingController();
  final _imageNote = TextEditingController();
  final _manualAddress = TextEditingController();
  final _farmName = TextEditingController();
  final _plotSector = TextEditingController();
  final _row = TextEditingController();
  final _plantNumber = TextEditingController();
  final _picker = ImagePicker();
  final _recorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();

  String? _activeSessionId;
  File? _image;
  GeoData? _location;
  File? _voiceFile;
  bool _sending = false;
  bool _listening = false;
  bool _recording = false;
  bool _transcribing = false;
  bool _locating = false;

  @override
  void initState() {
    super.initState();
    _activeSessionId = widget.sessionId;
  }

  @override
  void dispose() {
    _message.dispose();
    _imageNote.dispose();
    _manualAddress.dispose();
    _farmName.dispose();
    _plotSector.dispose();
    _row.dispose();
    _plantNumber.dispose();
    _recorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _attachImage() async {
    final l = AppLocalizations.of(context);
    try {
      final picked = await _picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 88,
        maxWidth: 2200,
      );
      if (picked == null || !mounted) return;
      setState(() {
        _image = File(picked.path);
        _voiceFile = null;
      });
      await _captureLocation(silent: true);
    } catch (_) {
      if (!mounted) return;
      _show(l.photoPermissionHelp);
    }
  }

  Future<void> _captureLocation({bool silent = false}) async {
    final l = AppLocalizations.of(context);
    setState(() => _locating = true);
    try {
      final result = await ref.read(locationServiceProvider).current();
      if (!mounted) return;
      setState(() {
        _location = result;
        if ((result.address ?? '').trim().isNotEmpty) {
          _manualAddress.text = result.address!.trim();
        }
      });
      if (!silent) _show(l.locationCaptured);
    } on AppException {
      if (!mounted || silent) return;
      _show(l.locationPermissionDenied);
    } catch (_) {
      if (!mounted || silent) return;
      _show(l.locationUnavailable);
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _toggleLiveSpeech() async {
    final l = AppLocalizations.of(context);
    final service = ref.read(liveSpeechProvider);
    if (_listening) {
      await service.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }

    try {
      setState(() => _listening = true);
      await service.listen(
        language: Localizations.localeOf(context).languageCode,
        onText: (text) {
          if (!mounted || text.trim().isEmpty) return;
          setState(() {
            _message.text = text;
            _message.selection = TextSelection.collapsed(offset: text.length);
          });
        },
      );
    } catch (_) {
      if (mounted) _show(l.micPermissionHelp);
    }
  }

  Future<void> _toggleRecording() async {
    final l = AppLocalizations.of(context);
    if (_recording) {
      final path = await _recorder.stop();
      if (!mounted) return;
      setState(() {
        _recording = false;
        _voiceFile = path == null ? null : File(path);
        _image = null;
      });
      return;
    }

    if (!await _recorder.hasPermission()) {
      _show(l.micPermissionHelp);
      return;
    }

    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/banana_voice_${DateTime.now().millisecondsSinceEpoch}.wav';
    try {
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
          autoGain: true,
          echoCancel: true,
          noiseSuppress: true,
        ),
        path: path,
      );
      if (mounted) setState(() => _recording = true);
    } catch (_) {
      if (mounted) _show(l.micPermissionHelp);
    }
  }

  Future<void> _previewVoice() async {
    final file = _voiceFile;
    if (file == null) return;
    await _audioPlayer.stop();
    await _audioPlayer.setFilePath(file.path);
    await _audioPlayer.play();
  }

  Future<void> _sendVoice() async {
    final l = AppLocalizations.of(context);
    final file = _voiceFile;
    if (file == null || _sending || _transcribing) return;
    setState(() => _transcribing = true);
    try {
      final transcript = await ref.read(chatRepositoryProvider).transcribe(
            file,
            Localizations.localeOf(context).languageCode,
          );
      if (transcript.trim().isEmpty) {
        throw const AppException('No transcript');
      }
      _message.text = transcript.trim();
      await _send(audio: file);
      if (mounted) setState(() => _voiceFile = null);
    } catch (_) {
      if (mounted) _show(l.voiceNoteFailed);
    } finally {
      if (mounted) setState(() => _transcribing = false);
    }
  }

  Future<void> _send({File? audio}) async {
    final l = AppLocalizations.of(context);
    final text = _message.text.trim();
    final imageNote = _imageNote.text.trim();
    final effectiveText = text.isNotEmpty ? text : imageNote;

    if (effectiveText.isEmpty) {
      _show(l.requiredField);
      return;
    }
    if (_sending) return;

    final image = _image;
    final manualAddress = _manualAddress.text.trim();
    final location = image == null
        ? null
        : GeoData(
            latitude: _location?.latitude,
            longitude: _location?.longitude,
            address: manualAddress.isNotEmpty
                ? manualAddress
                : _location?.address,
            farmName: _farmName.text.trim().isEmpty
                ? null
                : _farmName.text.trim(),
            plotSector: _plotSector.text.trim().isEmpty
                ? null
                : _plotSector.text.trim(),
            row: _row.text.trim().isEmpty ? null : _row.text.trim(),
            plantNumber: _plantNumber.text.trim().isEmpty
                ? null
                : _plantNumber.text.trim(),
          );

    setState(() => _sending = true);
    try {
      final response = await ref.read(chatRepositoryProvider).send(
            sessionId: _activeSessionId,
            text: effectiveText,
            language: Localizations.localeOf(context).languageCode,
            relatedScanId: widget.relatedScanId,
            image: image,
            audio: audio,
            location: location,
            note: imageNote.isEmpty ? null : imageNote,
          );
      final sid = response['session_id'] as String?;
      if (!mounted) return;
      setState(() {
        _activeSessionId = sid ?? _activeSessionId;
        _message.clear();
        _imageNote.clear();
        _manualAddress.clear();
        _farmName.clear();
        _plotSector.clear();
        _row.clear();
        _plantNumber.clear();
        _image = null;
        _location = null;
      });
    } on AppException catch (e) {
      if (!mounted) return;
      _show(e.message.contains('not ready') ? l.ragUnavailable : l.chatSendFailed);
    } catch (_) {
      if (mounted) _show(l.chatSendFailed);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _show(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final sessionId = _activeSessionId;
    final messages = sessionId == null
        ? const AsyncData<List<ChatMessage>>([])
        : ref.watch(chatMessagesProvider(sessionId));

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(color: AppColors.forest, borderRadius: BorderRadius.circular(13)),
              child: const Icon(Icons.eco_rounded, color: Colors.white),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l.bananaExpert, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  Text(l.expertSubtitle, style: const TextStyle(color: AppColors.muted, fontSize: 9)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsetsDirectional.only(end: 12),
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(99)),
            child: Center(child: Text(lang == 'ur' ? l.urdu : l.english, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w900))),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
              color: AppColors.leafSoft,
              child: Row(
                children: [
                  const Icon(Icons.menu_book_outlined, color: AppColors.forest, size: 17),
                  const SizedBox(width: 7),
                  Expanded(child: Text(l.chatContextNote, style: const TextStyle(color: AppColors.forest, fontSize: 9.5, height: 1.35, fontWeight: FontWeight.w700))),
                ],
              ),
            ),
            Expanded(
              child: messages.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, _) => Center(child: Text(l.errorTryAgain)),
                data: (items) {
                  if (items.isEmpty) {
                    return _EmptyChat(relatedScanId: widget.relatedScanId);
                  }
                  return ListView.builder(
                    reverse: false,
                    padding: const EdgeInsets.fromLTRB(14, 16, 14, 16),
                    itemCount: items.length,
                    itemBuilder: (_, index) => _MessageBubble(
                      message: items[index],
                      onSpeak: () => ref.read(ttsProvider).speak(items[index].text, lang),
                      onPause: () => ref.read(ttsProvider).pause(),
                      onStop: () => ref.read(ttsProvider).stop(),
                      onPlayAudio: items[index].audioUrl == null
                          ? null
                          : () async {
                              await _audioPlayer.stop();
                              await _audioPlayer.setUrl(items[index].audioUrl!);
                              await _audioPlayer.play();
                            },
                    ),
                  );
                },
              ),
            ),
            if (_sending || _transcribing)
              LinearProgressIndicator(
                minHeight: 2,
                color: AppColors.forest,
                backgroundColor: AppColors.leafSoft,
              ),
            if (_image != null) _ImageAttachmentPanel(
              image: _image!,
              noteController: _imageNote,
              addressController: _manualAddress,
              farmNameController: _farmName,
              plotSectorController: _plotSector,
              rowController: _row,
              plantNumberController: _plantNumber,
              locating: _locating,
              location: _location,
              onLocation: _captureLocation,
              onRemove: () => setState(() {
                _image = null;
                _imageNote.clear();
                _manualAddress.clear();
                _farmName.clear();
                _plotSector.clear();
                _row.clear();
                _plantNumber.clear();
                _location = null;
              }),
            ),
            if (_voiceFile != null)
              Container(
                margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(18)),
                child: Row(
                  children: [
                    const Icon(Icons.graphic_eq_rounded, color: AppColors.forest),
                    const SizedBox(width: 8),
                    Expanded(child: Text(l.voiceNoteReady, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11))),
                    IconButton(onPressed: _previewVoice, icon: const Icon(Icons.play_arrow_rounded), tooltip: l.playVoice),
                    IconButton(onPressed: _transcribing ? null : _sendVoice, icon: const Icon(Icons.send_rounded), tooltip: l.sendVoiceNote),
                    IconButton(onPressed: () => setState(() => _voiceFile = null), icon: const Icon(Icons.close_rounded), tooltip: l.close),
                  ],
                ),
              ),
            Container(
              padding: const EdgeInsets.fromLTRB(10, 9, 10, 12),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: AppColors.border)),
              ),
              child: Column(
                children: [
                  if (_recording)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.fiber_manual_record, color: AppColors.danger, size: 14),
                          const SizedBox(width: 6),
                          Text(l.recording, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w900, fontSize: 11)),
                        ],
                      ),
                    ),
                  Row(
                    children: [
                      IconButton.filledTonal(
                        onPressed: _sending ? null : _attachImage,
                        icon: const Icon(Icons.add_photo_alternate_outlined),
                        tooltip: l.attachImage,
                      ),
                      IconButton.filledTonal(
                        onPressed: _sending ? null : _toggleLiveSpeech,
                        icon: Icon(_listening ? Icons.mic_rounded : Icons.mic_none_rounded),
                        tooltip: l.voiceQuestion,
                      ),
                      IconButton.filledTonal(
                        onPressed: _sending ? null : _toggleRecording,
                        icon: Icon(_recording ? Icons.stop_circle_outlined : Icons.graphic_eq_rounded),
                        tooltip: _recording ? l.stopRecording : l.recordVoiceNote,
                      ),
                      const SizedBox(width: 5),
                      Expanded(
                        child: TextField(
                          controller: _message,
                          minLines: 1,
                          maxLines: 4,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _send(),
                          decoration: InputDecoration(
                            hintText: _listening ? l.listening : l.chatPlaceholder,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      IconButton.filled(
                        onPressed: _sending ? null : () => _send(),
                        icon: const Icon(Icons.send_rounded),
                        tooltip: l.send,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyChat extends StatelessWidget {
  const _EmptyChat({this.relatedScanId});
  final String? relatedScanId;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: const BoxDecoration(color: AppColors.leafSoft, shape: BoxShape.circle),
              child: const Icon(Icons.support_agent_rounded, size: 44, color: AppColors.forest),
            ),
            const SizedBox(height: 16),
            Text(l.chatEmpty, textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 7),
            Text(l.expertSubtitle, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted)),
            if (relatedScanId != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(99)),
                child: Text(l.relatedScan, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 10)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ImageAttachmentPanel extends StatelessWidget {
  const _ImageAttachmentPanel({
    required this.image,
    required this.noteController,
    required this.addressController,
    required this.farmNameController,
    required this.plotSectorController,
    required this.rowController,
    required this.plantNumberController,
    required this.locating,
    required this.location,
    required this.onLocation,
    required this.onRemove,
  });

  final File image;
  final TextEditingController noteController;
  final TextEditingController addressController;
  final TextEditingController farmNameController;
  final TextEditingController plotSectorController;
  final TextEditingController rowController;
  final TextEditingController plantNumberController;
  final bool locating;
  final GeoData? location;
  final VoidCallback onLocation;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: AppColors.border)),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(borderRadius: BorderRadius.circular(14), child: Image.file(image, width: 76, height: 76, fit: BoxFit.cover)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.imageAttached, style: const TextStyle(fontWeight: FontWeight.w900)),
                    const SizedBox(height: 4),
                    Text(l.chatImageLeafOnly, style: const TextStyle(color: AppColors.muted, fontSize: 9.5, height: 1.35)),
                  ],
                ),
              ),
              IconButton(onPressed: onRemove, icon: const Icon(Icons.close_rounded), tooltip: l.removePhoto),
            ],
          ),
          const SizedBox(height: 9),
          TextField(
            controller: noteController,
            maxLines: 2,
            decoration: InputDecoration(labelText: l.addImageNote, prefixIcon: const Icon(Icons.notes_rounded)),
          ),
          const SizedBox(height: 8),
          Text(
            l.exactFarmPlace,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 7),
          TextField(
            controller: farmNameController,
            decoration: InputDecoration(
              labelText: l.farmName,
              prefixIcon: const Icon(Icons.agriculture_outlined),
            ),
          ),
          const SizedBox(height: 7),
          TextField(
            controller: plotSectorController,
            decoration: InputDecoration(
              labelText: l.plotSector,
              prefixIcon: const Icon(Icons.grid_view_rounded),
            ),
          ),
          const SizedBox(height: 7),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: rowController,
                  decoration: InputDecoration(labelText: l.row),
                ),
              ),
              const SizedBox(width: 7),
              Expanded(
                child: TextField(
                  controller: plantNumberController,
                  decoration: InputDecoration(labelText: l.plantNumber),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            controller: addressController,
            decoration: InputDecoration(
              labelText: l.manualAddress,
              prefixIcon: const Icon(Icons.location_on_outlined),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  location?.latitude == null
                      ? l.locationOptional
                      : '${location!.latitude!.toStringAsFixed(5)}, ${location!.longitude!.toStringAsFixed(5)}',
                  style: const TextStyle(color: AppColors.muted, fontSize: 9.5),
                ),
              ),
              TextButton.icon(
                onPressed: locating ? null : onLocation,
                icon: locating
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.my_location_rounded, size: 17),
                label: Text(l.captureLocation),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.onSpeak,
    required this.onPause,
    required this.onStop,
    this.onPlayAudio,
  });

  final ChatMessage message;
  final VoidCallback onSpeak;
  final VoidCallback onPause;
  final VoidCallback onStop;
  final VoidCallback? onPlayAudio;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final user = message.sender == 'user';
    return Align(
      alignment: user ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 340),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: user ? AppColors.bananaSoft : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: Radius.circular(user ? 20 : 5),
            bottomRight: Radius.circular(user ? 5 : 20),
          ),
          border: Border.all(color: user ? AppColors.banana.withValues(alpha: .30) : AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if ((message.imageUrl ?? '').isNotEmpty) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Image.network(
                  message.imageUrl!,
                  height: 170,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) => Container(height: 100, color: AppColors.leafSoft),
                ),
              ),
              const SizedBox(height: 8),
            ],
            if ((message.audioUrl ?? '').isNotEmpty && onPlayAudio != null) ...[
              InkWell(
                onTap: onPlayAudio,
                borderRadius: BorderRadius.circular(99),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                  decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(99)),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.play_arrow_rounded, color: AppColors.forest, size: 19),
                      const SizedBox(width: 5),
                      Text(l.playVoice, style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w900, fontSize: 10)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
            if ((message.note ?? '').trim().isNotEmpty) ...[
              Text(message.note!, style: const TextStyle(color: AppColors.muted, fontStyle: FontStyle.italic, fontSize: 10.5)),
              const SizedBox(height: 5),
            ],
            if (message.location != null &&
                (message.location!.placeLabel.isNotEmpty ||
                    (message.location!.address ?? '').trim().isNotEmpty ||
                    message.location!.latitude != null)) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.location_on_outlined, size: 15, color: AppColors.forest),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      [
                        if (message.location!.placeLabel.isNotEmpty)
                          message.location!.placeLabel,
                        if ((message.location!.address ?? '').trim().isNotEmpty)
                          message.location!.address!.trim(),
                        if (message.location!.latitude != null &&
                            message.location!.longitude != null)
                          '${message.location!.latitude!.toStringAsFixed(5)}, '
                              '${message.location!.longitude!.toStringAsFixed(5)}',
                      ].join(' • '),
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 9.5,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
            ],
            Text(message.text, style: const TextStyle(fontSize: 12, height: 1.5)),
            if (!user) ...[
              const SizedBox(height: 9),
              Wrap(
                spacing: 3,
                children: [
                  TextButton.icon(onPressed: onSpeak, icon: const Icon(Icons.volume_up_outlined, size: 16), label: Text(l.listen)),
                  IconButton(onPressed: onPause, icon: const Icon(Icons.pause_rounded, size: 18), tooltip: l.pause),
                  IconButton(onPressed: onStop, icon: const Icon(Icons.stop_rounded, size: 18), tooltip: l.stop),
                ],
              ),
            ],
            if (message.sources.isNotEmpty) ...[
              const Divider(height: 18),
              Text(l.conversationSources, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 9.5)),
              const SizedBox(height: 4),
              ...message.sources.map(
                (source) => Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Text(
                    '• ${source.title}${source.page == null ? '' : ' — ${l.sourcePage(source.page!)}'}',
                    style: const TextStyle(color: AppColors.muted, fontSize: 9),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
