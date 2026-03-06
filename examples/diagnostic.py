"""Diagnostic test app for all speech-to-text features.

Each button tests a single feature. Status text shows results and errors.
"""

import json
import flet as ft
from flet_stt import FletStt


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    stt = FletStt()
    is_listening = False

    log = ft.Text("ready", selectable=True, size=12)
    result_text = ft.Text("", selectable=True, size=16, weight="bold")
    level_bar = ft.ProgressBar(value=0, width=300, color=ft.Colors.BLUE)

    def set_log(msg):
        log.value = msg
        page.update()

    def on_result(e):
        data = json.loads(e.data)
        prefix = "[FINAL]" if data["final"] else "[partial]"
        confidence = f" ({data['confidence']:.0%})" if data["confidence"] > 0 else ""
        result_text.value = f"{prefix} {data['text']}{confidence}"
        page.update()

    def on_sound_level(e):
        data = json.loads(e.data)
        # Normalize dB level to 0-1 range (typically -2 to -40 dB)
        normalized = max(0, min(1, (data["level"] + 40) / 38))
        level_bar.value = normalized
        page.update()

    def on_error(e):
        data = json.loads(e.data)
        permanent = " (PERMANENT)" if data["permanent"] else ""
        set_log(f"ERROR: {data['error']}{permanent}")

    def on_status(e):
        nonlocal is_listening
        data = json.loads(e.data)
        status = data["status"]
        is_listening = status == "listening"
        set_log(f"status: {status}")

    stt.on_result = on_result
    stt.on_sound_level = on_sound_level
    stt.on_error = on_error
    stt.on_status = on_status

    async def init_stt(e):
        available = await stt.initialize()
        set_log(f"initialized: {'available' if available else 'NOT available'}")

    async def start_listening(e):
        result_text.value = ""
        level_bar.value = 0
        page.update()
        await stt.listen(partial_results=True, listen_mode="dictation")

    async def start_listening_cloud(e):
        result_text.value = ""
        level_bar.value = 0
        page.update()
        await stt.listen(on_device=False, partial_results=True, listen_mode="dictation")

    async def start_listening_ro(e):
        result_text.value = ""
        level_bar.value = 0
        page.update()
        await stt.listen(locale_id="ro_RO", partial_results=True, listen_mode="dictation")

    async def stop_listening(e):
        await stt.stop()

    async def cancel_listening(e):
        await stt.cancel()
        result_text.value = "(cancelled)"
        page.update()

    async def show_locales(e):
        locales = await stt.locales()
        names = [f"{loc['id']}: {loc['name']}" for loc in locales[:20]]
        set_log(f"{len(locales)} locales:\n" + "\n".join(names))

    def hint(text):
        return ft.Text(text, size=10, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER)

    page.add(
        ft.Column(
            [
                ft.Text("flet-stt diagnostic", size=20, weight="bold"),
                log,
                ft.Divider(),
                result_text,
                level_bar,
                ft.Divider(),
                ft.Button(content="1. Initialize", on_click=init_stt),
                hint("must be called first — checks availability + requests mic permission"),
                ft.Divider(height=1),
                ft.Button(content="2. Listen (system language)", on_click=start_listening),
                hint("starts recognition in system default locale.\n"
                     "speak and watch partial results appear in real-time."),
                ft.Divider(height=1),
                ft.Button(content="3. Listen (Romanian)", on_click=start_listening_ro),
                hint("starts recognition in ro_RO locale.\n"
                     "requires Romanian language pack installed."),
                ft.Divider(height=1),
                ft.Button(content="4. Listen (cloud)", on_click=start_listening_cloud),
                hint("starts recognition with on_device=False.\n"
                     "fires cloud_recognition_timeout error after 5s\n"
                     "if cloud is unavailable."),
                ft.Divider(height=1),
                ft.Button(content="5. Stop (get final result)", on_click=stop_listening),
                hint("stops listening and triggers the final result."),
                ft.Divider(height=1),
                ft.Button(content="6. Cancel (discard)", on_click=cancel_listening),
                hint("cancels listening without returning a result."),
                ft.Divider(height=1),
                ft.Button(content="7. List locales", on_click=show_locales),
                hint("shows available speech recognition languages.\n"
                     "first 20 shown in log."),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
    )


ft.run(main)
