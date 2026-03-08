"""Simple speech-to-text example with start/stop toggle.

Tap the mic to start listening, tap again to stop.
Shows partial results while speaking, final result when done.
"""

import flet as ft
from flet_stt import FletStt, SttResult, SttErrorData, SttStatus


def main(page: ft.Page):
    stt = FletStt()
    is_listening = False

    result = ft.Text("Tap the mic and speak", size=16)
    status_text = ft.Text("idle", size=12, color=ft.Colors.GREY_600)
    mic_btn = ft.IconButton(ft.Icons.MIC, icon_size=48)

    def on_result(e):
        r = SttResult(e)
        prefix = "" if r.final else "..."
        result.value = f"{prefix} {r.text}"
        page.update()

    def on_error(e):
        err = SttErrorData(e)
        status_text.value = f"error: {err.error}"
        status_text.color = ft.Colors.RED
        page.update()

    def on_status(e):
        nonlocal is_listening
        s = SttStatus(e)
        is_listening = s.listening
        status_text.value = s.status
        status_text.color = ft.Colors.GREEN if s.listening else ft.Colors.GREY_600
        mic_btn.icon = ft.Icons.MIC_OFF if s.listening else ft.Icons.MIC
        page.update()

    stt.on_result = on_result
    stt.on_error = on_error
    stt.on_status = on_status

    async def toggle_listen(e):
        nonlocal is_listening
        if is_listening:
            await stt.stop()
        else:
            await stt.initialize()
            await stt.listen()

    mic_btn.on_click = toggle_listen

    page.add(
        ft.Column(
            [result, status_text, mic_btn],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


ft.run(main)
