"""Locale picker example.

Lists available speech recognition languages, lets the user pick one,
then listens in that language.
"""

import json
import flet as ft
from flet_stt import FletStt


def main(page: ft.Page):
    stt = FletStt()
    selected_locale = ""

    result = ft.Text("", size=16, selectable=True)
    locale_dropdown = ft.Dropdown(
        label="Language",
        width=300,
    )

    def on_result(e):
        data = json.loads(e.data)
        prefix = "[FINAL]" if data["final"] else ""
        result.value = f"{prefix} {data['text']}"
        page.update()

    stt.on_result = on_result

    async def load_locales(e):
        available = await stt.initialize()
        if not available:
            result.value = "Speech recognition not available"
            page.update()
            return

        locales = await stt.locales()
        locale_dropdown.options = [
            ft.Option(key=loc["id"], text=f"{loc['name']} ({loc['id']})")
            for loc in locales
        ]
        page.update()

    def on_locale_select(e):
        nonlocal selected_locale
        selected_locale = e.control.value

    locale_dropdown.on_change = on_locale_select

    async def listen_selected(e):
        if not selected_locale:
            result.value = "Pick a language first"
            page.update()
            return

        result.value = f"Listening in {selected_locale}..."
        page.update()
        await stt.listen(
            locale_id=selected_locale,
            partial_results=True,
            listen_mode="dictation",
        )

    async def stop(e):
        await stt.stop()

    page.add(
        ft.Column(
            [
                ft.Text("Locale picker", size=20, weight="bold"),
                ft.Button(content="Load languages", on_click=load_locales),
                locale_dropdown,
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Button(content="Listen", on_click=listen_selected),
                        ft.Button(content="Stop", on_click=stop),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                result,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
    )


ft.run(main)
