import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "flet_stt" / "src"))

from flet_stt import FletStt, SttError, SttErrorData, SttResult, SttSoundLevel, SttStatus


class Event:
    def __init__(self, data):
        self.data = json.dumps(data)


class EventWrapperTests(unittest.TestCase):
    def test_result_wrapper_parses_payload(self):
        result = SttResult(
            Event(
                {
                    "text": "hello",
                    "final": True,
                    "confidence": 0.9,
                    "alternates": [{"text": "yellow", "confidence": 0.2}],
                }
            )
        )

        self.assertEqual(result.text, "hello")
        self.assertTrue(result.final)
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.alternates[0]["text"], "yellow")

    def test_error_status_and_sound_level_wrappers(self):
        error = SttErrorData(Event({"error": "error_speech_timeout", "permanent": False}))
        status = SttStatus(Event({"status": "done"}))
        sound_level = SttSoundLevel(Event({"level": -6.5}))

        self.assertEqual(error.error, "error_speech_timeout")
        self.assertFalse(error.permanent)
        self.assertTrue(status.done)
        self.assertFalse(status.listening)
        self.assertEqual(sound_level.level, -6.5)


class FletSttMethodTests(unittest.IsolatedAsyncioTestCase):
    def test_check_error_raises_stt_error(self):
        stt = FletStt()

        with self.assertRaisesRegex(SttError, "boom"):
            stt._check_error("error:boom")

    async def test_listen_passes_current_speech_options_to_dart(self):
        stt = FletStt()
        stt._initialized = True
        calls = []

        async def invoke_method(**kwargs):
            calls.append(kwargs)
            return "ok"

        stt._invoke_method = invoke_method

        await stt.listen(
            locale_id="ro_RO",
            listen_for_seconds=30,
            pause_for_seconds=4,
            partial_results=False,
            on_device=True,
            cancel_on_error=True,
            sample_rate=44100,
            listen_mode="dictation",
            auto_punctuation=True,
            enable_haptic_feedback=True,
            cloud_timeout_seconds=0,
            continuous=True,
        )

        self.assertEqual(calls[0]["method_name"], "listen")
        self.assertEqual(
            calls[0]["arguments"],
            {
                "locale_id": "ro_RO",
                "listen_for_seconds": 30,
                "pause_for_seconds": 4,
                "partial_results": False,
                "on_device": True,
                "cancel_on_error": True,
                "sample_rate": 44100,
                "listen_mode": "dictation",
                "auto_punctuation": True,
                "enable_haptic_feedback": True,
                "cloud_timeout_seconds": 0,
                "continuous": True,
            },
        )

    async def test_listen_requires_initialize(self):
        stt = FletStt()

        with self.assertRaisesRegex(SttError, "initialize"):
            await stt.listen()

    async def test_initialize_passes_options_to_dart(self):
        stt = FletStt()
        calls = []

        async def invoke_method(**kwargs):
            calls.append(kwargs)
            return "true"

        stt._invoke_method = invoke_method

        with patch.object(FletStt, "page", new_callable=PropertyMock) as page:
            page.return_value = SimpleNamespace(web=False)
            available = await stt.initialize(debug_logging=True, final_timeout_seconds=1.5)

        self.assertTrue(available)
        self.assertTrue(stt._initialized)
        self.assertEqual(calls[0]["method_name"], "initialize")
        self.assertEqual(
            calls[0]["arguments"],
            {"debug_logging": True, "final_timeout_ms": 1500},
        )
