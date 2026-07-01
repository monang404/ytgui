import json
import time
import secrets
from config import ADMIN_USERNAME, ADMIN_PASSWORD
from core.security import verify_password
from core.constants import MAX_LOGIN_ATTEMPTS
def _prune_stale_ips(manager, now: float) -> None:
    """Hapus entry IP yang sudah melewati window dari kedua dict rate-limit.
    Dipanggil tiap handle_auth agar dict tidak tumbuh tanpa batas (memory leak).
    """
    WINDOW_AUTH = 300
    WINDOW_CMD  = 60

    stale_auth = [ip for ip, ts_list in manager.login_attempts.items()
                  if not any(now - t < WINDOW_AUTH for t in ts_list)]
    for ip in stale_auth:
        del manager.login_attempts[ip]

    stale_cmd = [ip for ip, ts_list in manager.command_history.items()
                 if not any(now - t < WINDOW_CMD for t in ts_list)]
    for ip in stale_cmd:
        del manager.command_history[ip]


async def handle_auth(ws, data, manager, client_ip, db, now):
    async with manager.rl_lock:
        _prune_stale_ips(manager, now)

        token = data.get("token")
        if token and db:
            if await db.verify_session(token):
                manager.authenticated_connections.add(ws)
                await ws.send_str(json.dumps({
                    "type": "auth_status",
                    "data": {"success": True, "token": token}
                }))
                return

        attempts = manager.login_attempts.get(client_ip, [])
        attempts = [t for t in attempts if now - t < 300]
        if not attempts:
            manager.login_attempts.pop(client_ip, None)
        else:
            manager.login_attempts[client_ip] = attempts
        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            await ws.send_str(json.dumps({
                "type": "auth_status",
                "data": {"success": False, "message": "Terlalu banyak percobaan login. Coba lagi dalam 5 menit."}
            }))
            return

        username = data.get("username", "")
        password = data.get("password", "")
        if secrets.compare_digest(username, ADMIN_USERNAME) and verify_password(password, ADMIN_PASSWORD):
            new_token = secrets.token_hex(16)
            if db:
                await db.create_session(new_token, int(now) + 86400)
            manager.authenticated_connections.add(ws)
            if client_ip in manager.login_attempts:
                del manager.login_attempts[client_ip]
            await ws.send_str(json.dumps({
                "type": "auth_status",
                "data": {"success": True, "token": new_token}
            }))
        else:
            attempts.append(now)
            manager.login_attempts[client_ip] = attempts
            await ws.send_str(json.dumps({
                "type": "auth_status",
                "data": {"success": False, "message": "Username atau Password salah!"}
            }))

def require_auth(manager, ws) -> bool:
    return ws in manager.authenticated_connections
