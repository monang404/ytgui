import json
import time
import secrets
from config import ADMIN_USERNAME, ADMIN_PASSWORD
from core.security import verify_password

async def handle_auth(ws, data, manager, client_ip, db, now):
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
    if len(attempts) >= 5:
        await ws.send_str(json.dumps({
            "type": "auth_status",
            "data": {"success": False, "message": "Terlalu banyak percobaan login. Coba lagi dalam 5 menit."}
        }))
        return

    username = data.get("username", "")
    password = data.get("password", "")
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD):
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
