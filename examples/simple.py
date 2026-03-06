"""Simplest possible speech-to-text example.

Tap the mic button, speak, see the result.
"""

import json
import flet as ft
from flet_stt import FletStt


def main(page: ft.Page):
    stt = FletStt()
    result = ft.Text("Tap the mic and speak", size=16)

    def on_result(e):
        data = json.loads(e.data)
        if data["final"]:
            result.value = data["text"]
            page.update()

    stt.on_result = on_result

    async def toggle_listen(e):
        await stt.initialize()
        await stt.listen()

    page.add(
        ft.Column(
            [
                result,
                ft.IconButton(
                    ft.Icons.MIC,
                    icon_size=48,
                    on_click=toggle_listen,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


ft.run(main)
