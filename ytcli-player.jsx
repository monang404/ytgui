import { useState, useEffect, useRef } from "react";

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
// Palette terinspirasi dari CRT terminal + waveform audio visualizer
// #0D0D0D  bg-void      hitam "studio gelap"
// #141420  bg-panel     panel sedikit lebih terang
// #1E1E30  bg-elevated  elevated card / active state
// #FF6B35  accent-fire  warna asli app (equalizer)
// #FFC107  accent-gold  warna asli app (search/controls)
// #A0A0C0  text-muted   abu-ungu untuk metadata
// #E8E8FF  text-primary teks utama (putih kebiruan, bukan putih keras)

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0D0D0D;
    color: #E8E8FF;
    font-family: 'Inter', sans-serif;
    height: 100vh;
    overflow: hidden;
  }

  .mono { font-family: 'Space Mono', monospace; }

  /* SCROLLBAR */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2a2a45; border-radius: 2px; }

  /* EQUALIZER BARS */
  @keyframes bar1 { 0%,100%{height:4px} 50%{height:22px} }
  @keyframes bar2 { 0%,100%{height:14px} 30%{height:6px} 70%{height:20px} }
  @keyframes bar3 { 0%,100%{height:8px} 40%{height:24px} }
  @keyframes bar4 { 0%,100%{height:18px} 60%{height:4px} }
  @keyframes bar5 { 0%,100%{height:10px} 25%{height:22px} 75%{height:6px} }

  .eq-bar { width: 3px; border-radius: 2px 2px 0 0; background: #FF6B35; align-self: flex-end; }
  .eq-bar.paused { animation: none !important; height: 3px !important; background: #555; }
  .eq-bar:nth-child(1) { animation: bar1 0.8s ease-in-out infinite; }
  .eq-bar:nth-child(2) { animation: bar2 0.6s ease-in-out infinite; }
  .eq-bar:nth-child(3) { animation: bar3 1.1s ease-in-out infinite; }
  .eq-bar:nth-child(4) { animation: bar4 0.7s ease-in-out infinite; }
  .eq-bar:nth-child(5) { animation: bar5 0.9s ease-in-out infinite; }
  .eq-bar:nth-child(6) { animation: bar2 1.0s ease-in-out infinite 0.2s; }
  .eq-bar:nth-child(7) { animation: bar3 0.75s ease-in-out infinite 0.1s; }
  .eq-bar:nth-child(8) { animation: bar1 0.85s ease-in-out infinite 0.3s; }

  /* PROGRESS BAR */
  .progress-track {
    height: 3px; background: #2a2a45; border-radius: 2px;
    cursor: pointer; position: relative;
  }
  .progress-fill {
    height: 100%; background: linear-gradient(90deg, #FF6B35, #FFC107);
    border-radius: 2px; transition: width 0.3s linear;
    position: relative;
  }
  .progress-fill::after {
    content: '';
    position: absolute; right: -5px; top: -4px;
    width: 11px; height: 11px; border-radius: 50%;
    background: #FFC107; opacity: 0;
    transition: opacity 0.15s;
  }
  .progress-track:hover .progress-fill::after { opacity: 1; }

  /* CONTROL BUTTON */
  .ctrl-btn {
    display: flex; align-items: center; justify-content: center;
    background: #1E1E30; border: 1px solid #2a2a45;
    border-radius: 10px; cursor: pointer;
    transition: all 0.15s ease; color: #A0A0C0;
    font-family: 'Space Mono', monospace; font-size: 11px;
    gap: 6px; user-select: none; outline: none;
  }
  .ctrl-btn:hover { background: #2a2a45; border-color: #444470; color: #E8E8FF; transform: translateY(-1px); }
  .ctrl-btn:active { transform: translateY(0); background: #303050; }
  .ctrl-btn.primary {
    background: #FF6B35; border-color: #FF6B35; color: #fff;
    box-shadow: 0 0 18px rgba(255,107,53,0.3);
  }
  .ctrl-btn.primary:hover { background: #ff7d4a; border-color: #ff7d4a; box-shadow: 0 0 24px rgba(255,107,53,0.45); }
  .ctrl-btn.active-toggle { border-color: #FFC107; color: #FFC107; }

  /* SEARCH */
  .search-box {
    background: #1E1E30; border: 1px solid #2a2a45;
    border-radius: 10px; padding: 10px 14px;
    color: #E8E8FF; font-family: 'Inter', sans-serif; font-size: 14px;
    outline: none; width: 100%; transition: border-color 0.15s;
  }
  .search-box:focus { border-color: #FFC107; box-shadow: 0 0 0 3px rgba(255,193,7,0.1); }
  .search-box::placeholder { color: #555580; }

  /* TRACK ITEM */
  .track-item {
    padding: 10px 12px; border-radius: 8px;
    cursor: pointer; transition: background 0.12s;
    display: flex; align-items: center; gap: 10px;
  }
  .track-item:hover { background: #1E1E30; }
  .track-item.current { background: #1E1E30; border-left: 2px solid #FF6B35; }

  /* PANEL */
  .panel {
    background: #141420; border: 1px solid #1E1E30;
    border-radius: 14px; overflow: hidden;
  }
  .panel-header {
    padding: 10px 16px; border-bottom: 1px solid #1E1E30;
    font-family: 'Space Mono', monospace; font-size: 11px;
    color: #555580; letter-spacing: 0.08em; text-transform: uppercase;
    display: flex; align-items: center; justify-content: space-between;
  }

  /* LYRICS */
  .lyric-line { padding: 3px 0; transition: all 0.3s ease; color: #555580; font-size: 13px; }
  .lyric-line.active { color: #FFC107; font-size: 14px; font-weight: 500; }

  /* STATUS DOT */
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .status-dot { width: 7px; height: 7px; border-radius: 50%; }
  .status-dot.online { background: #4ade80; animation: pulse 2s ease-in-out infinite; }
  .status-dot.offline { background: #ef4444; }

  /* VOLUME SLIDER */
  input[type=range] {
    -webkit-appearance: none; height: 3px;
    background: #2a2a45; border-radius: 2px; outline: none; cursor: pointer;
    width: 100%;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 12px; height: 12px;
    border-radius: 50%; background: #FFC107; cursor: pointer;
  }
  input[type=range]:focus { outline: none; }

  /* SEARCH RESULT */
  .result-item {
    padding: 10px 14px; border-radius: 8px; cursor: pointer;
    display: flex; align-items: center; gap: 10px;
    transition: background 0.12s;
  }
  .result-item:hover { background: #1E1E30; }

  /* SCROLLABLE AREA */
  .scroll-area { overflow-y: auto; }

  @keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
  .fade-in { animation: fadeIn 0.2s ease; }

  /* KEYBOARD HINT BADGE */
  .kbd {
    display: inline-flex; align-items: center; justify-content: center;
    background: #0D0D0D; border: 1px solid #2a2a45;
    border-radius: 4px; padding: 1px 5px;
    font-family: 'Space Mono', monospace; font-size: 10px;
    color: #555580; line-height: 1.4;
  }
`;

// ─── FAKE DATA ─────────────────────────────────────────────────────────────────
const DEMO_QUEUE = [
  { id: "1", title: "Yellow", artist: "Coldplay", duration: 269, views: "892M" },
  { id: "2", title: "The Scientist", artist: "Coldplay", duration: 309, views: "678M" },
  { id: "3", title: "Fix You", artist: "Coldplay", duration: 295, views: "1.1B" },
  { id: "4", title: "Clocks", artist: "Coldplay", duration: 307, views: "445M" },
];

const DEMO_LYRICS = [
  { time: 0, text: "Look at the stars" },
  { time: 5, text: "Look how they shine for you" },
  { time: 10, text: "And everything you do" },
  { time: 15, text: "Yeah, they were all yellow" },
  { time: 22, text: "I came along" },
  { time: 28, text: "I wrote a song for you" },
  { time: 34, text: "And all the things you do" },
  { time: 40, text: "And it was called 'Yellow'" },
  { time: 47, text: "So then I took my turn" },
  { time: 53, text: "Oh, what a thing to have done" },
  { time: 58, text: "And it was all yellow" },
];

const DEMO_RESULTS = [
  { id: "r1", title: "Yellow - Official Video", artist: "Coldplay", duration: 269, views: "892M" },
  { id: "r2", title: "Yellow (Live in Buenos Aires)", artist: "Coldplay", duration: 285, views: "234M" },
  { id: "r3", title: "Yellow (Acoustic)", artist: "Coldplay", duration: 241, views: "45M" },
  { id: "r4", title: "Yellow (Piano Cover)", artist: "PianoCovers", duration: 258, views: "12M" },
  { id: "r5", title: "Best of Coldplay Full Album", artist: "Coldplay", duration: 3600, views: "78M" },
];

// ─── HELPERS ────────────────────────────────────────────────────────────────────
function fmtTime(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function Equalizer({ playing }) {
  return (
    <div style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 28 }}>
      {[...Array(8)].map((_, i) => (
        <div key={i} className={`eq-bar ${!playing ? "paused" : ""}`} />
      ))}
    </div>
  );
}

// ─── MAIN COMPONENT ─────────────────────────────────────────────────────────────
export default function YTPlayer() {
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(42);
  const [volume, setVolume] = useState(80);
  const [radioMode, setRadioMode] = useState(false);
  const [showLyrics, setShowLyrics] = useState(true);
  const [queue, setQueue] = useState(DEMO_QUEUE.slice(1));
  const [currentTrack] = useState(DEMO_QUEUE[0]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [isOnline] = useState(true);
  const [activePanel, setActivePanel] = useState("queue"); // "queue" | "lyrics"
  const searchRef = useRef(null);
  const intervalRef = useRef(null);

  // Simulate progress
  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        setPosition(p => p >= currentTrack.duration ? 0 : p + 1);
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [playing, currentTrack.duration]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (showSearch) return;
      switch (e.key.toLowerCase()) {
        case "p": setPlaying(p => !p); break;
        case "/": e.preventDefault(); setShowSearch(true); setTimeout(() => searchRef.current?.focus(), 50); break;
        case "r": setRadioMode(r => !r); break;
        case "l": setShowLyrics(s => !s); break;
        case "u": setVolume(v => Math.min(100, v + 5)); break;
        case "d": setVolume(v => Math.max(0, v - 5)); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [showSearch]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSearchResults(DEMO_RESULTS);
    }
    setShowSearch(false);
  };

  const pct = (position / currentTrack.duration) * 100;
  const activeLyricIdx = DEMO_LYRICS.reduce((acc, l, i) => l.time <= position ? i : acc, 0);

  return (
    <>
      <style>{css}</style>
      <div style={{
        height: "100vh", display: "flex", flexDirection: "column",
        padding: "12px 14px", gap: 10, maxWidth: 900, margin: "0 auto"
      }}>

        {/* ── HEADER ── */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 2 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="mono" style={{ fontSize: 12, color: "#FF6B35", fontWeight: 700, letterSpacing: "0.1em" }}>
              YT PLAYER
            </span>
            <span style={{ fontSize: 10, color: "#2a2a45", fontFamily: "monospace" }}>v1.0</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className={`status-dot ${isOnline ? "online" : "offline"}`} />
            <span className="mono" style={{ fontSize: 10, color: "#555580" }}>
              {isOnline ? "ONLINE" : "OFFLINE"}
            </span>
            <span className="mono" style={{ fontSize: 10, color: "#2a2a45" }}>
              {new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>

        {/* ── BODY ── */}
        <div style={{ flex: 1, display: "flex", gap: 10, minHeight: 0 }}>

          {/* ── LEFT: NOW PLAYING ── */}
          <div style={{ width: 280, display: "flex", flexDirection: "column", gap: 10, flexShrink: 0 }}>
            <div className="panel" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <div className="panel-header">
                <span>Now Playing</span>
                {currentTrack.views && (
                  <span style={{ color: "#333360" }}>{currentTrack.views} views</span>
                )}
              </div>
              <div style={{ padding: "16px 16px 14px", flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                {/* Track info */}
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "#E8E8FF", lineHeight: 1.3, marginBottom: 4 }}>
                    {currentTrack.title}
                  </div>
                  <div style={{ fontSize: 12, color: "#A0A0C0" }}>{currentTrack.artist}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                    <span style={{ fontSize: 10, background: "#1E1E30", color: "#555580", padding: "2px 7px", borderRadius: 4 }}
                      className="mono">STREAM</span>
                    {radioMode && <span style={{ fontSize: 10, background: "rgba(255,193,7,0.12)", color: "#FFC107", padding: "2px 7px", borderRadius: 4 }}
                      className="mono">RADIO</span>}
                  </div>
                </div>

                {/* Equalizer */}
                <div style={{ display: "flex", justifyContent: "center", padding: "12px 0 8px" }}>
                  <Equalizer playing={playing} />
                </div>

                {/* Progress */}
                <div>
                  <div className="progress-track" onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const p = (e.clientX - rect.left) / rect.width;
                    setPosition(Math.floor(p * currentTrack.duration));
                  }}>
                    <div className="progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 5 }}>
                    <span className="mono" style={{ fontSize: 10, color: "#555580" }}>{fmtTime(position)}</span>
                    <span className="mono" style={{ fontSize: 10, color: "#555580" }}>{fmtTime(currentTrack.duration)}</span>
                  </div>
                </div>

                {/* Volume */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                  <span style={{ fontSize: 14 }}>🔈</span>
                  <input type="range" min={0} max={100} value={volume}
                    onChange={e => setVolume(+e.target.value)}
                    style={{ flex: 1 }} />
                  <span className="mono" style={{ fontSize: 10, color: "#A0A0C0", width: 32, textAlign: "right" }}>
                    {volume}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ── RIGHT ── */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>

            {/* SEARCH */}
            <div style={{ position: "relative" }}>
              {showSearch ? (
                <form onSubmit={handleSearch} className="fade-in">
                  <input
                    ref={searchRef}
                    className="search-box mono"
                    placeholder="Cari lagu atau artis..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === "Escape" && setShowSearch(false)}
                  />
                </form>
              ) : (
                <button
                  className="search-box"
                  style={{ textAlign: "left", cursor: "text", color: "#555580", fontSize: 13 }}
                  onClick={() => { setShowSearch(true); setTimeout(() => searchRef.current?.focus(), 50); }}
                >
                  <span style={{ marginRight: 8, opacity: 0.5 }}>🔍</span>
                  Tekan <span className="kbd">/</span> untuk mencari lagu...
                </button>
              )}
            </div>

            {/* SEARCH RESULTS or QUEUE+LYRICS */}
            {searchResults.length > 0 && !showSearch ? (
              <div className="panel fade-in" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
                <div className="panel-header">
                  <span>Hasil Pencarian</span>
                  <button onClick={() => setSearchResults([])}
                    style={{ background: "none", border: "none", color: "#555580", cursor: "pointer", fontSize: 11, fontFamily: "monospace" }}>
                    × Tutup
                  </button>
                </div>
                <div className="scroll-area" style={{ flex: 1, padding: 8 }}>
                  {searchResults.map((r, i) => (
                    <div key={r.id} className="result-item" onClick={() => setSearchResults([])}>
                      <span className="mono" style={{ fontSize: 10, color: "#333360", width: 16, flexShrink: 0 }}>{i + 1}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, color: "#E8E8FF", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {r.title}
                        </div>
                        <div style={{ fontSize: 11, color: "#A0A0C0", marginTop: 1 }}>{r.artist} · {r.views}</div>
                      </div>
                      <span className="mono" style={{ fontSize: 10, color: "#555580", flexShrink: 0 }}>{fmtTime(r.duration)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
                {/* Panel toggle tabs */}
                <div style={{ display: "flex", gap: 6 }}>
                  {["queue", "lyrics"].map(tab => (
                    <button key={tab} onClick={() => setActivePanel(tab)}
                      style={{
                        background: activePanel === tab ? "#1E1E30" : "transparent",
                        border: `1px solid ${activePanel === tab ? "#2a2a45" : "transparent"}`,
                        borderRadius: 8, padding: "5px 14px", cursor: "pointer",
                        color: activePanel === tab ? "#E8E8FF" : "#555580",
                        fontFamily: "Space Mono, monospace", fontSize: 10, letterSpacing: "0.07em",
                        textTransform: "uppercase", transition: "all 0.15s"
                      }}>
                      {tab === "queue" ? `Antrean (${queue.length})` : "Lirik"}
                    </button>
                  ))}
                </div>

                {/* QUEUE */}
                {activePanel === "queue" && (
                  <div className="panel fade-in" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
                    <div className="scroll-area" style={{ flex: 1, padding: 8 }}>
                      <div className="track-item current">
                        <Equalizer playing={playing} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, color: "#FF6B35", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {currentTrack.title}
                          </div>
                          <div style={{ fontSize: 11, color: "#A0A0C0" }}>{currentTrack.artist}</div>
                        </div>
                        <span className="mono" style={{ fontSize: 10, color: "#FF6B35" }}>{fmtTime(currentTrack.duration)}</span>
                      </div>
                      {queue.map((t, i) => (
                        <div key={t.id} className="track-item">
                          <span className="mono" style={{ fontSize: 10, color: "#333360", width: 18, flexShrink: 0 }}>{i + 1}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, color: "#C0C0E0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.title}</div>
                            <div style={{ fontSize: 11, color: "#555580" }}>{t.artist}</div>
                          </div>
                          <span className="mono" style={{ fontSize: 10, color: "#333360" }}>{fmtTime(t.duration)}</span>
                        </div>
                      ))}
                      {queue.length === 0 && (
                        <div style={{ padding: "20px 12px", color: "#333360", fontSize: 12, textAlign: "center" }}>
                          Antrean kosong
                          {radioMode && <div style={{ color: "#FFC107", marginTop: 4, fontSize: 11 }}>Radio mode aktif — memutar otomatis</div>}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* LYRICS */}
                {activePanel === "lyrics" && (
                  <div className="panel fade-in" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
                    <div className="scroll-area" style={{ flex: 1, padding: "10px 16px" }}>
                      {DEMO_LYRICS.map((l, i) => (
                        <div key={i} className={`lyric-line ${i === activeLyricIdx ? "active" : ""}`}>
                          {l.text}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── CONTROLS BAR ── */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className="ctrl-btn" style={{ padding: "9px 14px" }}
            onClick={() => {}}>
            <span>⏮</span>
            <span className="kbd">B</span>
          </button>

          <button className={`ctrl-btn primary`} style={{ padding: "9px 22px", minWidth: 80 }}
            onClick={() => setPlaying(p => !p)}>
            <span style={{ fontSize: 16 }}>{playing ? "⏸" : "▶"}</span>
            <span style={{ fontSize: 11 }}>{playing ? "Pause" : "Play"}</span>
            <span className="kbd" style={{ background: "rgba(255,255,255,0.15)", border: "none", color: "rgba(255,255,255,0.7)" }}>P</span>
          </button>

          <button className="ctrl-btn" style={{ padding: "9px 14px" }}
            onClick={() => {}}>
            <span>⏭</span>
            <span className="kbd">N</span>
          </button>

          <div style={{ width: 1, height: 28, background: "#1E1E30" }} />

          <button className="ctrl-btn" style={{ padding: "9px 14px" }}
            onClick={() => {}}>
            <span>⏹</span>
            <span className="kbd">S</span>
          </button>

          <button className={`ctrl-btn ${radioMode ? "active-toggle" : ""}`} style={{ padding: "9px 14px" }}
            onClick={() => setRadioMode(r => !r)}>
            <span>📻</span>
            <span style={{ fontSize: 11 }}>Radio</span>
            <span className="kbd">R</span>
          </button>

          <button className={`ctrl-btn ${showLyrics ? "active-toggle" : ""}`} style={{ padding: "9px 14px" }}
            onClick={() => { setShowLyrics(s => !s); setActivePanel("lyrics"); }}>
            <span>🎵</span>
            <span className="kbd">L</span>
          </button>

          <button className="ctrl-btn" style={{ padding: "9px 14px" }}
            onClick={() => {}}>
            <span>💾</span>
            <span style={{ fontSize: 11 }}>Cache</span>
            <span className="kbd">M</span>
          </button>

          <div style={{ flex: 1 }} />

          <button className="ctrl-btn" style={{ padding: "9px 14px", borderColor: "#ef4444", color: "#ef4444" }}
            onClick={() => {}}>
            <span style={{ fontSize: 11 }}>Keluar</span>
            <span className="kbd">Q</span>
          </button>
        </div>

      </div>
    </>
  );
}
