import asyncio
import logging
from typing import Coroutine, Optional, Callable, Any

logger = logging.getLogger(__name__)

def safe_create_task(coro: Coroutine[Any, Any, Any], name: str = "", on_error: Optional[Callable[[Exception], Any]] = None) -> asyncio.Task:
    """
    Membungkus pembuatan asyncio.Task dengan penanganan error terpusat
    sehingga exception tidak menjadi 'Task exception was never retrieved'
    yang menyebabkan silent crash.
    """
    async def _wrap_coro():
        try:
            await coro
        except asyncio.CancelledError:
            # CancelledError adalah exception normal saat task di-cancel
            pass
        except Exception as e:
            logger.error(f"Error in background task '{name}': {e}", exc_info=True)
            if on_error:
                try:
                    if asyncio.iscoroutinefunction(on_error):
                        await on_error(e)
                    else:
                        on_error(e)
                except Exception as inner_e:
                    logger.error(f"Error in on_error callback for task '{name}': {inner_e}", exc_info=True)

    task = asyncio.create_task(_wrap_coro(), name=name)
    return task
