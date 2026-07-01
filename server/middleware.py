import time
from core.observability import ACTIVE_WEBSOCKETS
from core.constants import MAX_RATE_LIMIT


async def check_rate_limit(manager, client_ip: str, now: float) -> bool:
    async with manager.rl_lock:
        cmd_history = manager.command_history.get(client_ip, [])
        cmd_history = [t for t in cmd_history if now - t < 60]
        if not cmd_history:
            manager.command_history.pop(client_ip, None)
        else:
            manager.command_history[client_ip] = cmd_history
        if len(cmd_history) >= MAX_RATE_LIMIT:
            return False
        cmd_history.append(now)
        manager.command_history[client_ip] = cmd_history
        return True
