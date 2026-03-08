"""Advanced speech-to-text demo — showcases all flet-stt features.

Controls for pause duration, cancel on error, sample rate, listen mode,
on-device toggle, plus live status indicators for permission, listening
state, system locale, and sound level.
"""

import json
import flet as ft
from flet_stt import FletStt, SttError


def main(page: ft.Page):
    page.title = "flet-stt advanced demo"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    stt = FletStt()

    # --- status indicators ---
    locale_text = ft.Text("System locale: detecting...", size=14, color=ft.Colors.GREY)
    permission_text = ft.Text("Permission: unknown", size=14, color=ft.Colors.GREY)
    listening_chip = ft.Chip(
        label=ft.Text("not listening"),
        bgcolor=ft.Colors.GREY_300,
        leading=ft.Icon(ft.Icons.HEARING_DISABLED, size=16),
    )
    sound_bar = ft.ProgressBar(value=0, width=300, color=ft.Colors.GREEN)
    sound_label = ft.Text("Sound level: —", size=12, color=ft.Colors.GREY)

    # --- controls ---
    pause_slider = ft.Slider(min=0, max=10, divisions=10, value=3, label="{value}s")
    pause_label = ft.Text("Pause for: 3s (auto-stop after silence)", size=13)

    cancel_switch = ft.Switch(label="Cancel on error", value=True)
    on_device_switch = ft.Switch(label="On-device recognition", value=False)

    sample_rate_dd = ft.Dropdown(
        label="Sample rate",
        width=180,
        value="0",
        options=[
            ft.dropdown.Option("0", text="Default"),
            ft.dropdown.Option("8000", text="8 kHz"),
            ft.dropdown.Option("16000", text="16 kHz"),
            ft.dropdown.Option("44100", text="44.1 kHz"),
        ],
    )

    listen_mode_dd = ft.Dropdown(
        label="Listen mode",
        width=180,
        value="dictation",
        options=[
            ft.dropdown.Option("confirmation", text="Confirmation"),
            ft.dropdown.Option("search", text="Search"),
            ft.dropdown.Option("dictation", text="Dictation"),
        ],
    )

    # --- mic button + result ---
    mic_btn = ft.IconButton(
        ft.Icons.MIC,
        icon_size=56,
        icon_color=ft.Colors.WHITE,
        bgcolor=ft.Colors.BLUE,
    )
    result = ft.Text(
        "Configure settings above, then tap the mic",
        size=18,
        text_align=ft.TextAlign.CENTER,
        color=ft.Colors.GREY,
        width=320,
    )
    alternates_col = ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def update_listening_chip(active: bool):
        if active:
            listening_chip.label = ft.Text("listening")
            listening_chip.bgcolor = ft.Colors.RED_100
            listening_chip.leading = ft.Icon(ft.Icons.HEARING, size=16, color=ft.Colors.RED)
        else:
            listening_chip.label = ft.Text("not listening")
            listening_chip.bgcolor = ft.Colors.GREY_300
            listening_chip.leading = ft.Icon(ft.Icons.HEARING_DISABLED, size=16)

    def reset_mic():
        mic_btn.icon = ft.Icons.MIC
        mic_btn.bgcolor = ft.Colors.BLUE
        update_listening_chip(False)
        sound_bar.value = 0
        sound_label.value = "Sound level: —"

    def on_pause_change(e):
        v = int(pause_slider.value)
        if v == 0:
            pause_label.value = "Pause for: default (platform decides)"
        else:
            pause_label.value = f"Pause for: {v}s (auto-stop after silence)"
        page.update()

    pause_slider.on_change = on_pause_change

    def on_result(e):
        data = json.loads(e.data)
        conf = data.get("confidence", 0)
        if data["final"]:
            txt = data["text"] or "No speech detected"
            if data["text"] and conf > 0:
                result.value = f"{txt}\n(confidence: {conf:.0%})"
            else:
                result.value = txt
            result.color = None if data["text"] else ft.Colors.GREY

            # show alternates if available (skip first — it's the main result)
            alts = data.get("alternates", [])
            alternates_col.controls.clear()
            if len(alts) > 1:
                alternates_col.controls.append(
                    ft.Text("Alternates:", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700)
                )
                for alt in alts[1:]:
                    c = alt.get("confidence", 0)
                    alternates_col.controls.append(
                        ft.Text(f'"{alt["text"]}" ({c:.0%})', size=12, color=ft.Colors.GREY_600, italic=True)
                    )

            reset_mic()
            page.update()

    def on_error(e):
        data = json.loads(e.data)
        perm = "permanent" if data.get("permanent") else "transient"
        result.value = f"Error ({perm}): {data['error']}"
        result.color = ft.Colors.RED
        reset_mic()
        page.update()

    async def on_status(e):
        data = json.loads(e.data)
        status = data["status"]
        if status == "listening":
            update_listening_chip(True)
        elif status in ("notListening", "done"):
            update_listening_chip(False)
            sound_bar.value = 0
            sound_label.value = "Sound level: —"
            if status == "done" and result.value == "Listening...":
                result.value = "No speech detected — tap the mic to try again"
                result.color = ft.Colors.GREY
                reset_mic()
        page.update()

    def on_sound_level(e):
        data = json.loads(e.data)
        level = data["level"]
        # normalize dB roughly to 0-1 range (typically -2 to 10)
        normalized = max(0.0, min(1.0, (level + 2) / 12))
        sound_bar.value = normalized
        sound_label.value = f"Sound level: {level:.1f} dB"
        page.update()

    stt.on_result = on_result
    stt.on_error = on_error
    stt.on_status = on_status
    stt.on_sound_level = on_sound_level

    async def toggle_listen(e):
        if await stt.is_listening():
            await stt.stop()
            reset_mic()
        else:
            if not await stt.has_permission():
                try:
                    await stt.initialize()
                except SttError as exc:
                    result.value = str(exc)
                    result.color = ft.Colors.RED
                    permission_text.value = "Permission: denied"
                    permission_text.color = ft.Colors.RED
                    page.update()
                    return
                if not await stt.has_permission():
                    result.value = "Microphone permission denied — check app settings"
                    result.color = ft.Colors.RED
                    permission_text.value = "Permission: denied"
                    permission_text.color = ft.Colors.RED
                    page.update()
                    return
                permission_text.value = "Permission: granted"
                permission_text.color = ft.Colors.GREEN

            result.value = "Listening..."
            result.color = ft.Colors.GREY
            alternates_col.controls.clear()
            mic_btn.icon = ft.Icons.MIC_OFF
            mic_btn.bgcolor = ft.Colors.RED
            update_listening_chip(True)
            page.update()

            await stt.listen(
                listen_mode=listen_mode_dd.value,
                on_device=on_device_switch.value,
                pause_for_seconds=int(pause_slider.value),
                cancel_on_error=cancel_switch.value,
                sample_rate=int(sample_rate_dd.value),
            )
        page.update()

    async def init_stt(e=None):
        try:
            available = await stt.initialize()
        except SttError as exc:
            result.value = str(exc)
            result.color = ft.Colors.RED
            page.update()
            return
        if not available:
            result.value = "Speech recognition not available on this device"
            result.color = ft.Colors.RED
            page.update()
            return

        locale = await stt.system_locale()
        lang = locale.get("name", "unknown")
        locale_id = locale.get("id", "")
        locale_text.value = f"System locale: {lang} ({locale_id})"
        locale_text.color = None

        has_perm = await stt.has_permission()
        permission_text.value = f"Permission: {'granted' if has_perm else 'not yet granted'}"
        permission_text.color = ft.Colors.GREEN if has_perm else ft.Colors.ORANGE

        result.value = f"Ready — tap the mic to start ({lang})"
        page.update()

    mic_btn.on_click = toggle_listen
    page.on_connect = init_stt

    # --- layout ---
    page.add(
        ft.Column(
            [
                ft.Text("flet-stt advanced demo", size=22, weight=ft.FontWeight.BOLD),
                ft.Divider(),

                # status row
                ft.Row([locale_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([permission_text, listening_chip], alignment=ft.MainAxisAlignment.CENTER, spacing=16),

                ft.Divider(),

                # controls
                ft.Text("Listen settings", size=16, weight=ft.FontWeight.W_600),
                ft.Row([listen_mode_dd, sample_rate_dd], spacing=12, wrap=True),
                ft.Row([cancel_switch, on_device_switch], spacing=12, wrap=True),
                pause_label,
                pause_slider,

                ft.Divider(),

                # mic + result
                ft.Row([mic_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([result], alignment=ft.MainAxisAlignment.CENTER),
                alternates_col,

                # sound level
                ft.Row(
                    [ft.Column([sound_label, sound_bar], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


ft.run(main)
