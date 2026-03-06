"""Continuous listening example.

Automatically restarts recognition when Android's silence timeout fires,
creating a pseudo-continuous dictation experience.
"""

import json
import flet as ft
from flet_stt import FletStt


def main(page: ft.Page):
    stt = FletStt()
    listening = False
    full_text = []

    result = ft.Text("", size=16, selectable=True)
    status_text = ft.Text("idle", size=12, color=ft.Colors.GREY_600)

    def on_result(e):
        data = json.loads(e.data)
        if data["final"] and data["text"].strip():
            full_text.append(data["text"])
            result.value = " ".join(full_text)
            page.update()

    def on_status(e):
        nonlocal listening
        data = json.loads(e.data)
        status = data["status"]
        status_text.value = status
        page.update()

        # Auto-restart when recognition stops (silence timeout)
        if status == "done" and listening:
            async def _restart():
                await stt.listen(
                    partial_results=False,
                    listen_mode="dictation",
                )
            page.run_task(_restart)

    def on_error(e):
        nonlocal listening
        data = json.loads(e.data)
        # Stop auto-restart on permanent errors or cloud timeout
        if data["permanent"] or data["error"] == "cloud_recognition_timeout":
            listening = False
            status_text.value = f"error: {data['error']}"
            page.update()

    stt.on_result = on_result
    stt.on_status = on_status
    stt.on_error = on_error

    async def start(e):
        nonlocal listening
        listening = True
        full_text.clear()
        result.value = ""
        page.update()
        await stt.initialize()
        await stt.listen(partial_results=False, listen_mode="dictation")

    async def stop(e):
        nonlocal listening
        listening = False
        await stt.stop()

    page.add(
        ft.Column(
            [
                ft.Text("Continuous dictation", size=20, weight="bold"),
                status_text,
                ft.Container(height=10),
                result,
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Button(content="Start", on_click=start),
                        ft.Button(content="Stop", on_click=stop),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


ft.run(main)
