# flet-stt

Speech-to-text for Flet apps. Wraps the `speech_to_text` Flutter plugin through a custom Flet extension, giving your Python code access to the OS-native speech recognizer on Android and iOS.

On Android this uses Google Speech Services (on-device for ~50 languages, no API key needed). On iOS it uses Apple's SFSpeechRecognizer.

## Features

- real-time speech recognition with partial results and alternate transcriptions
- locale selection (50+ languages, on-device where available)
- sound level monitoring during listening
- listen modes: confirmation (short), search, dictation (long-form)
- configurable pause detection, sample rate, and error handling
- system locale detection, permission checking, listening state queries
- proper error and status callbacks

## Install

```bash
pip install flet-stt
# or
poetry add flet-stt
```

In your app's `pyproject.toml`, declare the Android permission and tell Flet where to find the extension for APK builds:

```toml
[project]
dependencies = [
    "flet>=0.82.0",
    "flet-stt",
]

[tool.flet.android.permission]
"android.permission.RECORD_AUDIO" = true

[tool.flet.app]
exclude = ["flet_stt"]

[tool.flet.dev_packages]
flet-stt = "flet_stt"
```

The `exclude` line prevents the extension source from being raw-copied into the APK, which would shadow the installed package and break imports.

## Usage

```python
import json
import flet as ft
from flet_stt import FletStt


def main(page: ft.Page):
    stt = FletStt()

    def on_result(e):
        data = json.loads(e.data)
        if data["final"]:
            print(f"Recognized: {data['text']} (confidence: {data['confidence']:.0%})")

    stt.on_result = on_result

    async def start_listening(e):
        await stt.initialize()
        await stt.listen(partial_results=True, listen_mode="dictation")

    async def stop_listening(e):
        await stt.stop()

    page.add(
        ft.Column([
            ft.Button(content="Listen", on_click=start_listening),
            ft.Button(content="Stop", on_click=stop_listening),
        ])
    )


ft.run(main)
```

Just instantiate `FletStt`. Do not add it to `page.overlay` or `page.controls` - it's a service, not a visual control, and it registers itself automatically.

See the [`examples/`](examples/) folder for more: [`basic.py`](examples/basic.py), [`simple.py`](examples/simple.py), [`continuous.py`](examples/continuous.py), [`locale_picker.py`](examples/locale_picker.py), [`diagnostic.py`](examples/diagnostic.py).

## API

### `FletStt(on_result=..., on_sound_level=..., on_error=..., on_status=...)`

The service. Instantiate once. All callbacks receive an event where `e.data` is a JSON string.

### Events

| Event | e.data format | Description |
|---|---|---|
| `on_result` | `{"text": "hello", "final": true, "confidence": 0.95, "alternates": [...]}` | Recognition result. `final=false` for partial results. |
| `on_sound_level` | `{"level": -6.5}` | Microphone dB level during listening. |
| `on_error` | `{"error": "error_speech_timeout", "permanent": false}` | Recognition error. Permanent errors require re-initialization. |
| `on_status` | `{"status": "listening"}` | Status change: `"listening"`, `"notListening"`, `"done"`. |

The `alternates` field in `on_result` is a list of `{"text": "...", "confidence": 0.0}` objects. The first entry matches the main `text` field. Additional entries are alternative transcriptions when the engine provides them (depends on platform/locale).

### `await initialize() -> bool`

Initialize the speech recognizer and check availability. Must be called before `listen()`. Requests microphone permission on first call. Returns `True` if speech recognition is available.

### `await listen(...)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `locale_id` | `str` | `""` | BCP-47 locale (e.g. `"en_US"`, `"ro_RO"`). Empty = system default. |
| `listen_for_seconds` | `int` | `0` | Max listen duration. 0 = platform default (~60s on Android). |
| `pause_for_seconds` | `int` | `0` | Auto-stop after this many seconds of silence. 0 = platform default. |
| `partial_results` | `bool` | `True` | Fire `on_result` for partial (non-final) results during recognition. |
| `on_device` | `bool` | `True` | Prefer on-device recognition when available. |
| `cancel_on_error` | `bool` | `False` | Cancel recognition on error instead of continuing. |
| `sample_rate` | `int` | `0` | Audio sample rate in Hz. 0 = platform default. 16000 is recommended for speech. |
| `listen_mode` | `str` | `"confirmation"` | One of `"confirmation"`, `"search"`, `"dictation"`. |

### `await stop()`

Stop listening and trigger the final recognition result.

### `await cancel()`

Cancel listening without triggering a final result.

### `await locales() -> list[dict]`

Get available locales. Returns list of `{"id": "en_US", "name": "English (United States)"}`.

### `await system_locale() -> dict`

Get the system's default speech recognition locale. Returns `{"id": "en_US", "name": "English (United States)"}`.

### `await is_listening() -> bool`

Check whether the speech recognizer is currently listening.

### `await has_permission() -> bool`

Check whether the app has microphone permission.

## Building the APK

```bash
flet build apk -v
```

Or use `build.py` for automated build + deploy (dev-only, has hardcoded local paths):

```bash
python build.py
python build.py --skip-flet    # reuse existing build dir
python build.py --skip-install  # build only, don't deploy
```

On Windows, set `PYTHONIOENCODING=utf-8` before building to avoid Unicode crashes from Rich's spinner characters.

### Installing on device

Always do a full uninstall before installing a new APK. Flet's `serious_python` caches the extracted Python environment and won't pick up code changes with `adb install -r`:

```bash
adb uninstall com.yourapp.package
adb install build/apk/app-release.apk
```

## Platform notes

### Android

- Uses Google Speech Services, pre-installed on all phones with Google Play Services
- On-device recognition available for ~50 languages (no internet needed)
- Auto-stops after ~5s of silence or ~60s total - use the continuous example pattern to work around this
- Requires `RECORD_AUDIO` permission (declared in pyproject.toml, requested at runtime by `initialize()`)

### iOS

- Uses Apple SFSpeechRecognizer
- On-device recognition since iOS 15 for major languages
- Requires `NSSpeechRecognitionUsageDescription` and `NSMicrophoneUsageDescription` in Info.plist

### Desktop

Does nothing. The service instantiates without error but recognition won't work since there's no native plugin backing it.

## How it works

```
your Python app
  -> FletStt (ft.Service)
    -> _invoke_method() over Flet protocol
      -> SttService (FletService, Dart)
        -> speech_to_text plugin
          -> Android SpeechRecognizer / iOS SFSpeechRecognizer
```

The extension is packaged as a standard Python package with a `flutter/` namespace directory containing the Dart code. When you run `flet build apk`, Flet discovers the Dart code in site-packages and includes it as a path dependency in the generated Flutter project.

## License

MIT
