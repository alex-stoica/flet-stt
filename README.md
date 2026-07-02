# flet-stt

Speech-to-text for Flet apps via OS-native recognition (Android/iOS).

## Install

```bash
pip install flet-stt
```

### App pyproject.toml setup

Three things are required in your app's `pyproject.toml` for APK builds:

```toml
[project]
dependencies = ["flet>=0.82.0", "flet-stt"]

# 1. microphone permission
[tool.flet.android.permission]
"android.permission.RECORD_AUDIO" = true

# 2. prevent source shadowing in APK
[tool.flet.app]
exclude = ["flet_stt"]

# 3. extension discovery
[tool.flet.dev_packages]
flet-stt = "flet_stt"
```

All three are needed. Missing any one causes silent failures or build errors.

## Quick start

```python
import flet as ft
from flet_stt import FletStt, SttResult

def main(page: ft.Page):
    stt = FletStt()  # do NOT add to page.overlay or page.controls

    def on_result(e):
        r = SttResult(e)
        if r.final:
            print(f"Recognized: {r.text} ({r.confidence:.0%})")

    stt.on_result = on_result

    async def start(e):
        await stt.initialize()
        await stt.listen(listen_mode="dictation")

    page.add(ft.Button(content="Listen", on_click=start))

ft.run(main)
```

More examples in [`examples/`](examples/).

## Common pitfalls

### 1. Do not add FletStt to page.overlay or page.controls

FletStt is a service, not a visual control. It registers itself automatically. Adding it to `page.overlay`, `page.controls`, or `page.add()` causes a red crash screen on Android with no useful error message.

```python
# WRONG - causes crash
stt = FletStt()
page.overlay.append(stt)

# CORRECT - just instantiate
stt = FletStt()
```

### 2. Always uninstall before reinstalling APK

Flet's `serious_python` caches the extracted Python environment. `adb install -r` silently runs old code.

```bash
adb uninstall com.yourapp.package
adb install build/apk/app-release.apk
```

### 3. on_device=True may silently produce no results

On-device speech models may not be installed on the device. Recognition starts, status says "listening", but no results come back and no error fires. The default is `on_device=False` (cloud) which includes a 15-second timeout that fires a `cloud_recognition_timeout` error if nothing comes back.

## API

### FletStt()

Instantiate once. Assign event handlers before calling `listen()`.

### Events

| Event | e.data | Description |
|---|---|---|
| `on_result` | `{"text": "...", "final": true, "confidence": 0.95, "alternates": [...]}` | Recognition result. `final=false` for partial results. |
| `on_error` | `{"error": "...", "permanent": false}` | Error. Includes `cloud_recognition_timeout` when cloud returns nothing. |
| `on_status` | `{"status": "listening"}` | Status: `"listening"`, `"notListening"`, `"done"`. |
| `on_sound_level` | `{"level": -6.5}` | Mic dB level during listening. |

Each event has a typed wrapper so you don't need to parse JSON manually:

| Wrapper | Fields | Example |
|---|---|---|
| `SttResult(e)` | `.text`, `.final`, `.confidence`, `.alternates` | `r = SttResult(e); print(r.text)` |
| `SttErrorData(e)` | `.error`, `.permanent` | `err = SttErrorData(e); print(err.error)` |
| `SttStatus(e)` | `.status`, `.listening`, `.done` | `s = SttStatus(e); if s.listening: ...` |
| `SttSoundLevel(e)` | `.level` | `s = SttSoundLevel(e); print(s.level)` |

### Methods

**`await initialize(debug_logging=False, final_timeout_seconds=2.0) -> bool`** - initialize recognizer,
request mic permission. Call before `listen()`. `debug_logging` enables verbose native logs;
`final_timeout_seconds` caps the wait for a final result after recognition ends.

**`await listen(...)`**

| Parameter | Default | Description |
|---|---|---|
| `locale_id` | `""` | BCP-47 locale (e.g. `"en_US"`). Empty = system default. |
| `listen_for_seconds` | `0` | Max duration. 0 = platform default (~60s). |
| `pause_for_seconds` | `0` | Silence before auto-stop. 0 = platform default. |
| `partial_results` | `True` | Fire `on_result` for partial results. |
| `on_device` | `False` | Use on-device recognition. Default is cloud. |
| `cancel_on_error` | `False` | Cancel on error instead of continuing. |
| `sample_rate` | `0` | Hz. 0 = platform default. |
| `listen_mode` | `"confirmation"` | `"confirmation"`, `"search"`, or `"dictation"`. |
| `auto_punctuation` | `False` | Auto-insert punctuation (iOS only, no-op on Android). |
| `enable_haptic_feedback` | `False` | Haptic feedback while listening (iOS only, no-op on Android). |
| `cloud_timeout_seconds` | `15` | Seconds before `cloud_recognition_timeout` error. 0 = no timeout. Only when `on_device=False`. |
| `continuous` | `False` | Auto-restart natively when the platform ends a session. Stops on `stop()`/`cancel()`, permanent errors, and cloud timeouts. |

**`await stop()`** - stop and get final result.

**`await cancel()`** - stop without final result.

**`await locales() -> list[dict]`** - available locales.

**`await system_locale() -> dict`** - system default locale.

**`await is_listening() -> bool`** / **`await has_permission() -> bool`**

## Platform notes

- **Android**: Google Speech Services. On-device for ~50 languages. Auto-stops after ~5s silence / ~60s total. Requires `RECORD_AUDIO`.
- **iOS**: Apple SFSpeechRecognizer. On-device since iOS 15 for major languages. Needs `NSSpeechRecognitionUsageDescription` and `NSMicrophoneUsageDescription` in Info.plist.
- **Desktop/Web**: unsupported. On web, `speech_to_text` 7.4.0 returns empty transcripts (Dart-to-JS binding bug, [flutter#86621](https://github.com/flutter/flutter/issues/86621)), so STT yields no text. Android/iOS work.

## Building APK

```bash
flet build apk -v
```

On Windows, set `PYTHONIOENCODING=utf-8` before building to avoid Unicode crashes.

## License

MIT
