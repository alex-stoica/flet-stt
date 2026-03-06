# examples

Example apps for flet-stt. Run any of them with `flet run <file>` on desktop for quick iteration, or build an APK with `flet build apk` to test on a real device.

All examples require `flet-stt` installed. Run on Android (or iOS) - desktop has no OS speech recognizer.

## simple.py

Minimal example. Tap the mic, speak, see the result. Good starting point for understanding the API.

## continuous.py

Auto-restarts recognition after Android's silence timeout, creating pseudo-continuous dictation. Demonstrates the `on_status` / `on_error` callback pattern for robust restart logic. Handles `cloud_recognition_timeout` by stopping the restart loop.

## locale_picker.py

Lists all available speech recognition languages, lets the user pick one, then listens in that locale. Shows how to use `locales()` and the `locale_id` parameter.

## diagnostic.py

Button-per-feature test app. Covers: initialize, listen (system language), listen (Romanian), listen (cloud / `on_device=False`), stop, cancel, and locale listing. Use this to verify the extension works end-to-end on a device.
