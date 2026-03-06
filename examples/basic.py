"""Basic speech-to-text demo.

Tap the mic button, speak, see the result. No extra controls.
"""

import json
import flet as ft
from flet_stt import FletStt, SttError


def main(page: ft.Page):
    stt = FletStt()
    listening = False

    mic_btn = ft.IconButton(
        ft.Icons.MIC,
        icon_size=48,
        icon_color=ft.Colors.WHITE,
        bgcolor=ft.Colors.BLUE,
    )
    result = ft.Text(
        "Tap the mic and start talking",
        size=18,
        text_align=ft.TextAlign.CENTER,
        color=ft.Colors.GREY,
    )

    def reset_mic():
        nonlocal listening
        listening = False
        mic_btn.icon = ft.Icons.MIC
        mic_btn.bgcolor = ft.Colors.BLUE

    def on_result(e):
        data = json.loads(e.data)
        if data["final"]:
            result.value = data["text"] or "No speech detected"
            result.color = None if data["text"] else ft.Colors.GREY
            reset_mic()
            page.update()

    def on_error(e):
        data = json.loads(e.data)
        result.value = f"Error: {data['error']}"
        result.color = ft.Colors.RED
        reset_mic()
        page.update()

    def on_status(e):
        nonlocal listening
        data = json.loads(e.data)
        if data["status"] == "done" and listening:
            reset_mic()
            if result.value == "Listening...":
                result.value = "No speech detected — tap the mic to try again"
                result.color = ft.Colors.GREY
            page.update()

    stt.on_result = on_result
    stt.on_error = on_error
    stt.on_status = on_status

    async def toggle_listen(e):
        nonlocal listening
        if listening:
            await stt.stop()
            reset_mic()
        else:
            result.value = "Listening..."
            result.color = ft.Colors.GREY
            mic_btn.icon = ft.Icons.MIC_OFF
            mic_btn.bgcolor = ft.Colors.RED
            page.update()
            try:
                available = await stt.initialize()
            except SttError as exc:
                result.value = str(exc)
                result.color = ft.Colors.RED
                reset_mic()
                page.update()
                return
            if not available:
                result.value = "Speech recognition not available on this device"
                result.color = ft.Colors.GREY
                reset_mic()
                page.update()
                return
            await stt.listen(listen_mode="dictation", on_device=False)
            listening = True
        page.update()

    mic_btn.on_click = toggle_listen

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(
        ft.Column(
            [mic_btn, result],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


ft.run(main)
