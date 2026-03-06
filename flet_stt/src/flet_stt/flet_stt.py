import json
import logging
from typing import Optional

import flet as ft
from flet.controls.control_event import ControlEventHandler

logger = logging.getLogger("flet_stt")


class SttError(Exception):
    """Raised when a speech-to-text operation fails on the native side."""

    pass


@ft.control("flet_stt")
class FletStt(ft.Service):
    """Speech-to-text service using OS-native recognition.

    Wraps the Flutter speech_to_text package. On Android this uses Google
    Speech Services (on-device for ~50 languages). On iOS it uses Apple's
    SFSpeechRecognizer.

    Events:
        on_result: Fires with recognition results.
            e.data is JSON: {"text": "hello", "final": true, "confidence": 0.95}
        on_sound_level: Fires with microphone dB level during listening.
            e.data is JSON: {"level": -6.5}
        on_error: Fires on recognition errors.
            e.data is JSON: {"error": "error_speech_timeout", "permanent": false}
        on_status: Fires on status changes.
            e.data is JSON: {"status": "listening"} or {"status": "notListening"} or {"status": "done"}
    """

    on_result: Optional[ControlEventHandler["FletStt"]] = None
    on_sound_level: Optional[ControlEventHandler["FletStt"]] = None
    on_error: Optional[ControlEventHandler["FletStt"]] = None
    on_status: Optional[ControlEventHandler["FletStt"]] = None

    def _check_error(self, result):
        """Check if Dart returned an error and raise if so."""
        if isinstance(result, str) and result.startswith("error:"):
            raise SttError(result[6:])
        if result is None:
            logger.warning("service returned None (is the extension registered?)")
        return result

    async def initialize(self) -> bool:
        """Initialize the speech recognizer and check availability.

        Must be called before listen(). Requests microphone permission
        on first call.

        Returns:
            True if speech recognition is available, False otherwise.

        Raises:
            SttError: If initialization fails on the native side.
        """
        result = await self._invoke_method(method_name="initialize")
        checked = self._check_error(result)
        if checked == "true":
            return True
        if result is None:
            return False
        perm = await self.has_permission()
        if not perm:
            raise SttError("microphone permission denied - grant RECORD_AUDIO permission and try again")
        logger.info("speech recognition unavailable on this device")
        return False

    async def listen(
        self,
        *,
        locale_id: str = "",
        listen_for_seconds: int = 0,
        pause_for_seconds: int = 0,
        partial_results: bool = True,
        on_device: bool = True,
        cancel_on_error: bool = False,
        sample_rate: int = 0,
        listen_mode: str = "confirmation",
    ) -> None:
        """Start listening for speech.

        Args:
            locale_id: BCP-47 locale (e.g. "en_US", "ro_RO"). Empty = system default.
            listen_for_seconds: Max listen duration in seconds. 0 = platform default
                (typically ~60s on Android before auto-stop).
            pause_for_seconds: Auto-stop after this many seconds of silence. 0 = platform default.
            partial_results: If True, on_result fires for partial (non-final) results
                during recognition, not just the final result.
            on_device: Prefer on-device recognition when available. Falls back to
                cloud if on-device model isn't installed for the locale.
            cancel_on_error: If True, cancel recognition on error instead of continuing.
            sample_rate: Audio sample rate in Hz. 0 = platform default.
            listen_mode: Recognition mode. One of:
                - "confirmation": short phrases, yes/no responses (default)
                - "search": search query input
                - "dictation": longer free-form text

        Raises:
            SttError: If listening fails to start.
        """
        result = await self._invoke_method(
            method_name="listen",
            arguments={
                "locale_id": locale_id,
                "listen_for_seconds": listen_for_seconds,
                "pause_for_seconds": pause_for_seconds,
                "partial_results": partial_results,
                "on_device": on_device,
                "cancel_on_error": cancel_on_error,
                "sample_rate": sample_rate,
                "listen_mode": listen_mode,
            },
        )
        self._check_error(result)
        if result is not None and result != "ok":
            logger.debug("listen() returned unexpected: %s", result)

    async def stop(self) -> None:
        """Stop listening and trigger the final recognition result.

        After calling stop(), you'll receive one last on_result event with
        final=True containing the complete recognized text.

        Raises:
            SttError: If the stop operation fails.
        """
        result = await self._invoke_method(method_name="stop")
        self._check_error(result)
        if result is not None and result != "ok":
            logger.debug("stop() returned unexpected: %s", result)

    async def cancel(self) -> None:
        """Cancel listening without triggering a final result.

        Use this when the user wants to discard the current recognition
        session entirely.

        Raises:
            SttError: If the cancel operation fails.
        """
        result = await self._invoke_method(method_name="cancel")
        self._check_error(result)
        if result is not None and result != "ok":
            logger.debug("cancel() returned unexpected: %s", result)

    async def system_locale(self) -> dict:
        """Get the system's default speech recognition locale.

        Returns:
            Dict with "id" and "name" keys, e.g. {"id": "en_US", "name": "English (United States)"}.

        Raises:
            SttError: If the query fails.
        """
        result = await self._invoke_method(method_name="system_locale")
        self._check_error(result)
        return json.loads(result)

    async def is_listening(self) -> bool:
        """Check whether the speech recognizer is currently listening.

        Returns:
            True if actively listening, False otherwise.
        """
        result = await self._invoke_method(method_name="is_listening")
        self._check_error(result)
        return result == "true"

    async def has_permission(self) -> bool:
        """Check whether the app has microphone permission.

        Returns:
            True if permission is granted, False otherwise.
        """
        result = await self._invoke_method(method_name="has_permission")
        self._check_error(result)
        return result == "true"

    async def locales(self) -> list[dict]:
        """Get available speech recognition locales.

        Returns:
            List of dicts, each with "id" and "name" keys.
            Example: [{"id": "en_US", "name": "English (United States)"}, ...]

        Raises:
            SttError: If the query fails.
        """
        result = await self._invoke_method(method_name="locales")
        self._check_error(result)
        return json.loads(result)
