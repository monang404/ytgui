import asyncio
import sys

# Platform specific imports for non-blocking stdin read
if sys.platform == 'win32':
    import msvcrt
else:
    import tty
    import termios
    import select

from core.event_bus import (
    bus, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_RADIO,
    CMD_TOGGLE_LYRICS, CMD_QUIT, CMD_SEARCH, CMD_FOCUS_SEARCH, CMD_UNFOCUS
)

class InputHandler:
    def __init__(self, state):
        self.state = state
        self.is_searching = False
        self.search_buffer = ""

    async def run(self):
        """Async loop to continuously read keystrokes without blocking."""
        loop = asyncio.get_running_loop()  # HIGH-03: use get_running_loop
        
        fd = None
        old_settings = None
        if sys.platform != 'win32':
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            
        try:
            while True:
                # Run the blocking read in executor
                char = await loop.run_in_executor(None, self._read_char)
                if not char:
                    await asyncio.sleep(0.05)
                    continue
                
                await self._handle_char(char)
        finally:
            if sys.platform != 'win32' and fd is not None and old_settings is not None:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _read_char(self):
        """Reads a single character from stdin. Cross-platform.
        CRITICAL-02 fix: Uses select() with timeout on Linux/Termux
        so the thread is never blocked indefinitely."""
        if sys.platform == 'win32':
            if msvcrt.kbhit():
                return msvcrt.getch().decode('utf-8', errors='ignore')
            return None
        else:
            try:
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    return sys.stdin.read(1)
                return None
            except Exception:
                return None

    async def _handle_char(self, char: str):
        if self.is_searching:
            if char == '\r' or char == '\n':
                # Submit search
                self.is_searching = False
                query = self.search_buffer.strip()
                self.search_buffer = ""
                await bus.publish(CMD_UNFOCUS)
                if query:
                    await bus.publish(CMD_SEARCH, query)
            elif char == '\x1b': # Esc
                self.is_searching = False
                self.search_buffer = ""
                await bus.publish(CMD_UNFOCUS)
            elif char == '\x08' or char == '\x7f': # Backspace
                self.search_buffer = self.search_buffer[:-1]
            else:
                self.search_buffer += char
        else:
            char_lower = char.lower()
            if char == '/':
                self.is_searching = True
                await bus.publish(CMD_FOCUS_SEARCH)
            elif char_lower == 'p':
                await bus.publish(CMD_TOGGLE_PAUSE)
            elif char_lower == 'n':
                await bus.publish(CMD_NEXT)
            elif char_lower == 'b':
                await bus.publish(CMD_PREV)
            elif char_lower == 's':
                await bus.publish(CMD_STOP)
            elif char_lower == 'u':
                await bus.publish(CMD_VOLUME_UP)
            elif char_lower == 'd':
                await bus.publish(CMD_VOLUME_DOWN)
            elif char_lower == 'm':
                await bus.publish(CMD_DOWNLOAD)
            elif char_lower == 'r':
                await bus.publish(CMD_TOGGLE_RADIO)
            elif char_lower == 'l':
                await bus.publish(CMD_TOGGLE_LYRICS)
            elif char_lower == 'q' or char == '\x03': # Q or Ctrl+C
                await bus.publish(CMD_QUIT)
