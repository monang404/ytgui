#!/usr/bin/env bash
# test_radio_ws.sh — Tes langsung WebSocket backend ytgui untuk command set_mode RADIO.
# Tujuan: memastikan apakah backend benar-benar memproses toggle radio,
# TANPA lewat JS frontend sama sekali. Kalau script ini berhasil
# (status berubah ke RADIO + ada log pencarian lagu) tapi tombol di
# browser tetap tidak bereaksi, masalahnya ada di sisi JS/browser.
#
# Pakai Python3 + aiohttp (sudah ada di requirements.txt project ini),
# jadi tidak perlu install apa-apa lagi di Termux.
#
# Cara pakai:
#   chmod +x test_radio_ws.sh
#   ./test_radio_ws.sh
#
# Bisa override host/port/user/pass via env var:
#   YTGUI_HOST=127.0.0.1 YTGUI_PORT=8765 YTGUI_ADMIN_USER=admin YTGUI_ADMIN_PASS=rahasia ./test_radio_ws.sh

set -euo pipefail

HOST="${YTGUI_HOST:-127.0.0.1}"
PORT="${YTGUI_PORT:-8765}"
ADMIN_USER="${YTGUI_ADMIN_USER:-admin}"

if [ -z "${YTGUI_ADMIN_PASS:-}" ]; then
    read -r -s -p "Password admin: " ADMIN_PASS
    echo
else
    ADMIN_PASS="$YTGUI_ADMIN_PASS"
fi

WS_URL="ws://${HOST}:${PORT}/ws?room=default"

echo ""
echo "=== Menyambung ke ${WS_URL} ==="
echo ""

python3 - "$WS_URL" "$ADMIN_USER" "$ADMIN_PASS" << 'PYEOF'
import asyncio
import json
import sys

import aiohttp

WS_URL, USER, PASS = sys.argv[1], sys.argv[2], sys.argv[3]


def show(msg: str, data) -> None:
    print(f"\n[<<< {msg}]")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def main():
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.ws_connect(WS_URL) as ws:
            print("[OK] WebSocket terhubung.")

            # 1. Login sebagai admin
            await ws.send_str(json.dumps({
                "type": "cmd",
                "action": "auth",
                "data": {"username": USER, "password": PASS},
            }))
            print("[>>> auth] terkirim, menunggu balasan...")

            authed = False
            current_mode = None

            async def listen_for(seconds, on_each=None):
                nonlocal authed, current_mode
                try:
                    async with asyncio.timeout(seconds):
                        async for raw in ws:
                            if raw.type != aiohttp.WSMsgType.TEXT:
                                continue
                            msg = json.loads(raw.data)
                            mtype = msg.get("type")

                            if mtype == "auth_status":
                                show("auth_status", msg["data"])
                                authed = bool(msg["data"].get("success"))
                                if not authed:
                                    print("[GAGAL] Login admin ditolak. Cek username/password.")
                                    return
                            elif mtype == "state":
                                current_mode = msg["data"].get("playback_mode")
                                print(f"\n[<<< state] playback_mode = {current_mode} | "
                                      f"status = {msg['data'].get('status')}")
                            elif mtype == "log":
                                print(f"\n[<<< log] {msg['data']}")
                            elif mtype == "error":
                                print(f"\n[<<< ERROR DARI SERVER] {msg['data']}")
                            else:
                                show(mtype, msg.get("data"))

                            if on_each and on_each():
                                return
                except TimeoutError:
                    pass

            # Tunggu auth_status, lalu lanjut
            await listen_for(10, on_each=lambda: authed)

            if not authed:
                print("\n=== BERHENTI: tidak berhasil login. ===")
                return

            print("\n[OK] Login admin berhasil.")
            print("\n=== Mengirim command set_mode -> RADIO ===")
            await ws.send_str(json.dumps({
                "type": "cmd",
                "action": "set_mode",
                "data": {"mode": "RADIO"},
            }))
            print("[>>> set_mode RADIO] terkirim. Menunggu state/log selama 15 detik...")

            await listen_for(15)

            print("\n=== HASIL ===")
            if current_mode == "RADIO":
                print("[BERHASIL] Backend mengonfirmasi playback_mode = RADIO.")
                print("Kalau tombol di browser tetap tidak berubah warna,")
                print("masalahnya ada di JS frontend (listener/render), bukan backend.")
            else:
                print("[GAGAL/TIDAK JELAS] Tidak menerima konfirmasi playback_mode = RADIO.")
                print("Cek pesan 'log'/'ERROR DARI SERVER' di atas, atau cek ytplayer.log di server.")

            # Kembalikan ke QUEUE biar state nggak nyangkut di RADIO gara-gara tes ini
            print("\n=== Mengembalikan mode ke QUEUE ===")
            await ws.send_str(json.dumps({
                "type": "cmd",
                "action": "set_mode",
                "data": {"mode": "QUEUE"},
            }))
            await listen_for(5)


asyncio.run(main())
PYEOF
