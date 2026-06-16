from engine.ytdlp_client import YtDlpClient
from core.event_bus import bus, QUEUE_EMPTY, CMD_TOGGLE_RADIO, QUEUE_UPDATED, LOG_MESSAGE
from config import AUTOPLAY_THRESHOLD

class AutoplayEngine:
    """
    MED-12 fix: Improved search strategy — search by artist name
    instead of appending 'similar' which YouTube doesn't understand.
    """
    def __init__(self, ytdlp: YtDlpClient, state):
        self.ytdlp = ytdlp
        self.state = state
        bus.subscribe(QUEUE_EMPTY, self._on_queue_low)
        bus.subscribe(CMD_TOGGLE_RADIO, self._on_toggle)

    async def _on_toggle(self, _):
        self.state.is_radio_mode = not self.state.is_radio_mode
        state_str = "ON" if self.state.is_radio_mode else "OFF"
        await bus.publish(LOG_MESSAGE, f"Radio Mode: {state_str}")
        
        if self.state.is_radio_mode and len(self.state.queue) <= AUTOPLAY_THRESHOLD:
            await self._on_queue_low(None)

    async def _on_queue_low(self, _):
        if not self.state.is_radio_mode:
            return
        if not self.state.current_track:
            return

        # MED-12 fix: Better search strategy
        artist = self.state.current_track.artist
        query = f"{artist} music"
        await bus.publish(LOG_MESSAGE, f"Radio: Finding more from {artist}...")
        
        try:
            results = await self.ytdlp.search(query, max_results=5)
            
            # Filter out tracks already in queue or currently playing
            existing_ids = {t.video_id for t in self.state.queue}
            existing_ids.add(self.state.current_track.video_id)
            # Also filter from history to avoid repeats
            for t in self.state.history:
                existing_ids.add(t.video_id)
            
            new_tracks = [t for t in results if t.video_id not in existing_ids]
            
            if new_tracks:
                self.state.queue.extend(new_tracks[:3])
                await bus.publish(QUEUE_UPDATED)
                await bus.publish(LOG_MESSAGE, f"Radio: Added {len(new_tracks[:3])} tracks.")
            else:
                await bus.publish(LOG_MESSAGE, "Radio: No new tracks found.")
        except Exception as e:
            await bus.publish(LOG_MESSAGE, f"Radio Error: {e}")
