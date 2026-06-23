# AUDIT DEPENDENCY GRAPH — YTGUI Phase 3

---

## Module Dependency Graph (Per Package)

```mermaid
graph LR
    subgraph Entry
        MAIN[main.py]
    end

    subgraph Web["Web Layer"]
        WEB[web/server.py]
    end

    subgraph Engine["Engine Layer"]
        PC[playback_controller]
        QM[queue_mode]
        RM_E[radio_mode]
        VS[volume_service]
        DL[download_manager]
        CR[command_router]
        MPV[mpv_controller]
        YT[ytdlp_client]
    end

    subgraph Core["Core Layer"]
        EB[event_bus]
        CB[command_bus]
        ST[state]
        PT[ports]
        TU[task_utils]
        EV[events]
        SC[security]
        RM_C[room_manager]
        OBS[observability]
    end

    subgraph Cache["Cache Layer"]
        DB[cache/db]
        RES[cache/resolver]
    end

    subgraph Integrations["Integration Layer"]
        LF[lyrics]
        SB[sponsorblock]
        TN[termux_notification]
    end

    subgraph Config["Config"]
        CFG[config]
    end

    MAIN --> WEB
    MAIN --> RM_C
    MAIN --> DB
    MAIN --> YT
    MAIN --> DL
    MAIN --> CR
    MAIN --> TN
    MAIN --> CFG

    WEB --> CB
    WEB --> EB
    WEB --> RM_C
    WEB --> ST
    WEB --> CFG
    WEB --> SC

    CR --> CB
    CR --> RM_C

    RM_C --> MPV
    RM_C --> RES
    RM_C --> PC
    RM_C --> QM
    RM_C --> RM_E
    RM_C --> VS
    RM_C --> SB
    RM_C --> LF
    RM_C --> EB

    PC --> EB
    PC --> CB
    PC --> ST
    PC --> MPV
    PC --> RES
    PC --> SB
    PC --> LF
    PC --> QM
    PC --> RM_E
    PC --> TU

    MPV --> EB
    MPV --> CFG
    MPV --> TU

    DL --> EB
    DL --> CB
    DL --> YT
    DL --> TU

    LF --> EB
    SB --> EB
    TN --> EB
    TN --> CB

    RES --> DB
    RES --> YT
    RES --> CFG

    DB --> CFG
    YT --> CFG

    EB --> TU
    EB --> EV
    EB --> OBS
    CB --> OBS

    style EB fill:#ff9999,stroke:#ff0000
    style CB fill:#ffcc99,stroke:#ff6600
```

**Merah = Global Singleton (risiko tinggi)**  
**Orange = Singleton (risiko medium)**

---

## Circular Dependency Report

### Tidak Ditemukan Circular Import Langsung

Dependency direction sudah cukup baik:
- `core/` tidak import dari `engine/` atau `web/`
- `engine/` tidak import dari `web/`
- `cache/` tidak import dari `engine/`

### Deferred Import (Potensial Circular)

```
core/room_manager.py → (deferred) from core.event_bus import bus
```

Import ini dilakukan di dalam method bukan di top level. Ini biasanya menandakan ada upaya menghindari circular import. Saat ini tidak ada circular, tapi patut diperhatikan.

---

## Package Dependency Graph

```mermaid
graph TD
    subgraph External
        AIOHTTP[aiohttp]
        AIOSQLITE[aiosqlite]
        YTDLP[yt-dlp]
        STRUCTLOG[structlog]
        PROMETHEUS[prometheus-client]
        OTEL[opentelemetry-sdk]
        SYNCEDLYRICS[syncedlyrics]
        TEXTUAL[textual]
    end

    subgraph Internal
        CORE[core/]
        ENGINE[engine/]
        CACHE[cache/]
        WEB[web/]
        TUI[tui/]
        INTEGRATIONS[integrations/]
    end

    CORE --> STRUCTLOG
    CORE --> PROMETHEUS
    CORE --> OTEL
    ENGINE --> YTDLP
    ENGINE --> AIOHTTP
    CACHE --> AIOSQLITE
    WEB --> AIOHTTP
    TUI --> TEXTUAL
    INTEGRATIONS --> AIOHTTP
    INTEGRATIONS --> SYNCEDLYRICS
```

---

## Modul Paling Berisiko (berdasarkan coupling)

| Rank | Module | Fan-in (dependen) | Fan-out (bergantung) | Risk |
|---|---|---|---|---|
| 1 | `core/event_bus.py` | 10+ (semua modul) | 2 (task_utils, events) | 🔴 SANGAT TINGGI |
| 2 | `core/state.py` | 8+ | 0 | 🟠 TINGGI (perubahan cascade) |
| 3 | `config.py` | 8+ | 0 | 🟠 TINGGI (side effect) |
| 4 | `core/command_bus.py` | 6+ | 1 (observability) | 🟠 TINGGI |
| 5 | `web/server.py` | 0 | 10+ | 🟡 MEDIUM (god file) |
| 6 | `engine/playback_controller.py` | 2 (room_manager, command_router) | 8+ | 🟡 MEDIUM |
| 7 | `cache/db.py` | 4 (resolver, discover, main, web) | 1 (config) | 🟡 MEDIUM |

---

## Rekomendasi Dependency Restructuring

### Prioritas 1: Pisahkan Global EventBus

Masalah terbesar adalah `core/event_bus.py` memiliki singleton `bus` yang digunakan oleh hampir semua modul. Ini membuat refactor ke multi-room sejati tidak mungkin tanpa breaking change besar.

**Target State:**
```
core/event_bus.py  ← hanya class EventBus, tidak ada singleton
core/room_manager.py ← setiap Room membuat EventBus sendiri
```

### Prioritas 2: Config Tanpa Side Effect

`config.py` harus menjadi pure constants. Logika startup (password generation, file reading) pindah ke `startup.py` atau `AppConfig` class.

### Prioritas 3: Pisahkan `web/server.py`

Modul dengan fan-out besar dan logika yang bercampur adalah kandidat refactor untuk dipecah.
