#!/usr/bin/env python3
"""
bagas.fm — Server Manager
Jalankan: python start.py
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import sys
import os
import time
import webbrowser
from pathlib import Path
import socket
import importlib.util
import shutil
import secrets

# ── Config ────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
SERVER_PORT = int(os.environ.get("YTGUI_PORT", 8765))
PYTHON     = sys.executable

# ── Colors (bagas.fm dark theme) ─────────────────────────
BG         = "#0E0E12"
BG_SURFACE = "#151518"
BG_CARD    = "#1C1C22"
ACCENT     = "#F2B544"
TEXT_1     = "#FFFFFF"
TEXT_2     = "#9AA0AA"
TEXT_3     = "#60656F"
GREEN      = "#22C55E"
RED        = "#EF4444"
BORDER     = "#2A2A32"

class ServerManager(tk.Tk):
    def __init__(self):
        super().__init__()

        self.process: subprocess.Popen | None = None
        self._log_lock = threading.Lock()
        self._conflict_pid = None
        self._last_stdout_line = ""

        self._port_var = tk.StringVar(value=str(SERVER_PORT))

        self._build_window()
        self._build_ui()
        self._run_dependency_check()
        self._refresh_status()

    # ── Window setup ──────────────────────────────────────
    def _build_window(self):
        self.title("bagas.fm — Server Manager")
        self.geometry("600x680")
        self.minsize(520, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 600) // 2
        y = (self.winfo_screenheight() - 680) // 2
        self.geometry(f"+{x}+{y}")

        try:
            self.iconbitmap(default="")
        except Exception:
            pass

    # ── UI Layout ─────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG_SURFACE, pady=14)
        header.pack(fill="x")

        tk.Label(
            header, text="bagas.fm",
            bg=BG_SURFACE, fg=ACCENT,
            font=("Segoe UI", 18, "bold"),
        ).pack()
        tk.Label(
            header, text="Server Manager",
            bg=BG_SURFACE, fg=TEXT_3,
            font=("Segoe UI", 9),
        ).pack()

        # ── Status Card ──
        status_frame = tk.Frame(self, bg=BG_CARD, pady=12, padx=16)
        status_frame.pack(fill="x", padx=16, pady=(14, 0))

        left = tk.Frame(status_frame, bg=BG_CARD)
        left.pack(side="left")

        self._dot = tk.Canvas(
            left, width=10, height=10,
            bg=BG_CARD, highlightthickness=0
        )
        self._dot.pack(side="left", padx=(0, 8), pady=2)

        self._status_label = tk.Label(
            left, text="Checking...",
            bg=BG_CARD, fg=TEXT_2,
            font=("Segoe UI", 10, "bold"),
        )
        self._status_label.pack(side="left")

        # Port configuration input inside Status Frame
        port_frame = tk.Frame(status_frame, bg=BG_CARD)
        port_frame.pack(side="right")

        tk.Label(
            port_frame, text="Port:",
            bg=BG_CARD, fg=TEXT_3,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 4))

        self._port_entry = tk.Entry(
            port_frame, textvariable=self._port_var,
            bg=BG_SURFACE, fg=TEXT_1, font=("Consolas", 10),
            width=6, relief="flat", insertbackground=TEXT_1,
            justify="center", highlightthickness=1, highlightbackground=BORDER
        )
        self._port_entry.pack(side="left")

        self._pid_label = tk.Label(
            status_frame, text="",
            bg=BG_CARD, fg=TEXT_3,
            font=("Segoe UI", 9),
        )
        self._pid_label.pack(side="right", padx=(0, 12))

        # Conflict action panel (Kill conflicting process)
        self._btn_kill_conflict = tk.Button(
            status_frame, text="☠  Kill Conflict Process",
            fg=RED, bg="#2A0A0A", font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=6, pady=4,
            command=self._on_kill_conflict
        )

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg=BG, pady=10)
        btn_frame.pack(fill="x", padx=16)
        btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self._btn_start = self._make_btn(
            btn_frame, "▶  Start", ACCENT, "#2A1F06",
            self._on_start, col=0
        )
        self._btn_stop = self._make_btn(
            btn_frame, "■  Stop", RED, "#2A0A0A",
            self._on_stop, col=1
        )
        self._btn_restart = self._make_btn(
            btn_frame, "↺  Restart", TEXT_2, BG_CARD,
            self._on_restart, col=2
        )
        self._btn_open = self._make_btn(
            btn_frame, "⬡  Open Portal", TEXT_2, BG_CARD,
            self._on_open, col=3
        )

        # ── Admin Credentials Frame ──
        admin_frame = tk.Frame(self, bg=BG_CARD, pady=10, padx=16)
        admin_frame.pack(fill="x", padx=16, pady=(4, 0))

        tk.Label(
            admin_frame, text="🔑 ADMIN CREDENTIALS",
            bg=BG_CARD, fg=TEXT_3, font=("Segoe UI", 8, "bold")
        ).pack(side="left", anchor="w")

        tk.Label(
            admin_frame, text="User: admin  ·  Pass: [Hashed]",
            bg=BG_CARD, fg=TEXT_2, font=("Segoe UI", 9)
        ).pack(side="left", padx=15)

        btn_reset = tk.Button(
            admin_frame, text="Reset Password",
            bg=BG_SURFACE, fg=ACCENT, font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", bd=0,
            activebackground=BG_CARD, activeforeground=TEXT_1,
            padx=10, command=self._on_reset_password
        )
        btn_reset.pack(side="right")

        # Hover effect for reset button
        def on_enter_reset(e): btn_reset.config(bg=BG, fg=TEXT_1)
        def on_leave_reset(e): btn_reset.config(bg=BG_SURFACE, fg=ACCENT)
        btn_reset.bind("<Enter>", on_enter_reset)
        btn_reset.bind("<Leave>", on_leave_reset)

        # ── Quick Links Frame ──
        links_frame = tk.Frame(self, bg=BG_CARD, pady=10, padx=16)
        links_frame.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(
            links_frame, text="🌐 QUICK LINKS (CLICK TO OPEN)",
            bg=BG_CARD, fg=TEXT_3, font=("Segoe UI", 8, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        self._link_client = self._make_link(links_frame, "Client Portal", "/", 1, 0)
        self._link_admin = self._make_link(links_frame, "Admin Console", "/admin", 1, 1)
        self._link_health = self._make_link(links_frame, "System Health", "/health", 1, 2)
        self._link_metrics = self._make_link(links_frame, "Metrics API", "/metrics", 1, 3)

        # ── Dependencies Frame ──
        deps_frame = tk.Frame(self, bg=BG_CARD, pady=10, padx=16)
        deps_frame.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(
            deps_frame, text="⚙️ ENVIRONMENT & DEPENDENCIES",
            bg=BG_CARD, fg=TEXT_3, font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 6))

        self._deps_status = tk.Label(
            deps_frame, text="Checking environment dependencies...",
            bg=BG_CARD, fg=TEXT_2, font=("Segoe UI", 9),
            justify="left", anchor="w"
        )
        self._deps_status.pack(fill="x")

        # ── Log area ──
        log_header = tk.Frame(self, bg=BG, pady=0)
        log_header.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(
            log_header, text="LOG",
            bg=BG, fg=TEXT_3,
            font=("Segoe UI", 8, "bold"),
            anchor="w"
        ).pack(side="left")
        tk.Button(
            log_header, text="Clear",
            bg=BG, fg=TEXT_3,
            font=("Segoe UI", 8),
            relief="flat", cursor="hand2", bd=0,
            activebackground=BG, activeforeground=TEXT_2,
            command=self._clear_log
        ).pack(side="right")

        self._log = scrolledtext.ScrolledText(
            self,
            bg=BG_SURFACE, fg=TEXT_2,
            font=("Consolas", 8),
            relief="flat", bd=0,
            wrap="word",
            insertbackground=TEXT_2,
            selectbackground=ACCENT,
            state="disabled",
            padx=10, pady=8,
        )
        self._log.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        self._log.tag_config("accent", foreground=ACCENT)
        self._log.tag_config("err",    foreground=RED)
        self._log.tag_config("ok",     foreground=GREEN)
        self._log.tag_config("dim",    foreground=TEXT_3)

    def _make_btn(self, parent, text, fg, bg, cmd, col):
        b = tk.Button(
            parent, text=text,
            fg=fg, bg=bg,
            font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, cursor="hand2",
            activeforeground=fg,
            activebackground=BG_CARD,
            padx=8, pady=8,
            command=cmd,
        )
        b.grid(row=0, column=col, padx=3, sticky="ew")

        def on_enter(e):
            if b["state"] != "disabled":
                b.config(bg=BORDER, fg=TEXT_1)
        def on_leave(e):
            if b["state"] != "disabled":
                b.config(bg=bg, fg=fg)
        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        return b

    def _make_link(self, parent, text, path, row, col):
        lbl = tk.Label(
            parent, text=text,
            bg=BG_CARD, fg=TEXT_2,
            font=("Segoe UI", 9, "underline"),
            cursor="hand2"
        )
        lbl.grid(row=row, column=col, padx=8, pady=2, sticky="w")

        def open_url(event):
            port = self.server_port
            url = f"http://localhost:{port}{path}"
            webbrowser.open(url)
            self._write_log(f"Opening link: {url}", "dim")

        def on_enter(event):
            lbl.config(fg=ACCENT)

        def on_leave(event):
            lbl.config(fg=TEXT_2)

        lbl.bind("<Button-1>", open_url)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)
        return lbl

    # ── Helpers for Network and Port check ─────────────────
    @property
    def server_port(self) -> int:
        try:
            return int(self._port_var.get().strip())
        except ValueError:
            return 8765

    def _check_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def _get_pid_occupying_port(self, port: int) -> int | None:
        if sys.platform == "win32":
            try:
                output = subprocess.check_output('netstat -a -n -o', shell=True, text=True)
                for line in output.splitlines():
                    if "LISTENING" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            local_addr = parts[1]
                            pid = parts[-1]
                            if local_addr.endswith(f":{port}") or local_addr.endswith(f"]:{port}"):
                                return int(pid)
            except Exception:
                pass
        else:
            try:
                output = subprocess.check_output(f'lsof -t -i:{port}', shell=True, text=True)
                pids = output.strip().split()
                if pids:
                    return int(pids[0])
            except Exception:
                try:
                    output = subprocess.check_output(f'fuser {port}/tcp', shell=True, text=True)
                    parts = output.strip().split()
                    if parts:
                        return int(parts[-1])
                except Exception:
                    pass
        return None

    def _kill_process_tree(self, pid: int):
        if sys.platform == "win32":
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:
            try:
                import os
                import signal
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass

    # ── Dependency Checker ─────────────────────────────────
    def _check_dependencies(self):
        deps = {
            "yt-dlp": "yt_dlp",
            "aiosqlite": "aiosqlite",
            "aiohttp": "aiohttp",
            "syncedlyrics": "syncedlyrics",
            "structlog": "structlog",
            "prometheus_client": "prometheus_client",
            "opentelemetry": "opentelemetry"
        }
        missing = []
        for label, import_name in deps.items():
            try:
                spec = importlib.util.find_spec(import_name)
                if spec is None:
                    missing.append(label)
            except Exception:
                missing.append(label)
        
        mpv_ok = shutil.which("mpv") is not None
        return missing, mpv_ok

    def _run_dependency_check(self):
        def _thread_fn():
            missing, mpv_ok = self._check_dependencies()
            if not missing and mpv_ok:
                status_text = "✓ Python Libraries: OK  ·  ✓ MPV Audio Player: OK"
                color = GREEN
            else:
                parts = []
                if missing:
                    parts.append(f"✗ Missing libraries: {', '.join(missing)}")
                else:
                    parts.append("✓ Python Libraries: OK")
                if not mpv_ok:
                    parts.append("✗ MPV Player missing from PATH")
                else:
                    parts.append("✓ MPV Player: OK")
                status_text = "  ·  ".join(parts)
                color = RED
                
            self.after(0, lambda: self._deps_status.config(text=status_text, fg=color))
        
        threading.Thread(target=_thread_fn, daemon=True).start()

    # ── Status ────────────────────────────────────────────
    def _is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _refresh_status(self):
        port = self.server_port
        running = self._is_running()

        if running:
            status = "RUNNING"
            color = GREEN
            self._pid_label.config(text=f"PID {self.process.pid}  ·  :{port}")
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="normal")
            self._btn_restart.config(state="normal")
            self._btn_open.config(state="normal")
            self._port_entry.config(state="disabled")
            self._btn_kill_conflict.pack_forget()
        else:
            in_use = False
            conflict_pid = None
            if self._check_port_in_use(port):
                in_use = True
                conflict_pid = self._get_pid_occupying_port(port)

            if in_use:
                status = "CONFLICT"
                color = ACCENT
                pid_text = f"PID {conflict_pid}" if conflict_pid else "Unknown PID"
                self._pid_label.config(text=f"Port :{port} used by {pid_text}")
                self._btn_start.config(state="disabled")
                self._btn_stop.config(state="disabled")
                self._btn_restart.config(state="disabled")
                self._btn_open.config(state="normal")
                self._port_entry.config(state="normal")
                
                self._conflict_pid = conflict_pid
                self._btn_kill_conflict.config(text=f"☠  Kill Process (PID {conflict_pid})" if conflict_pid else "☠  Kill Port Owner")
                self._btn_kill_conflict.pack(side="right", padx=(5, 0))
            else:
                status = "STOPPED"
                color = RED
                self._pid_label.config(text=f"Port :{port}")
                self._btn_start.config(state="normal")
                self._btn_stop.config(state="disabled")
                self._btn_restart.config(state="disabled")
                self._btn_open.config(state="disabled")
                self._port_entry.config(state="normal")
                self._btn_kill_conflict.pack_forget()

        # Update Dot
        self._dot.delete("all")
        self._dot.create_oval(1, 1, 9, 9, fill=color, outline="")

        # Update status label text
        self._status_label.config(text=status, fg=color)

        self.after(2000, self._refresh_status)

    # ── Log helpers ───────────────────────────────────────
    def _write_log(self, msg: str, tag: str = ""):
        def _do():
            self._log.config(state="normal")
            ts = time.strftime("%H:%M:%S")
            self._log.insert("end", f"[{ts}] ", "dim")
            self._log.insert("end", msg.rstrip() + "\n", tag or "")
            self._log.see("end")
            self._log.config(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _pipe_stdout(self):
        """Baca stdout server, kirim ke log."""
        try:
            for line in self.process.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self._last_stdout_line = line
                tag = "err" if any(w in line.lower() for w in ("error", "exception", "traceback", "critical")) else \
                      "ok"  if any(w in line.lower() for w in ("started", "ready", "listening", "running")) else ""
                self._write_log(line, tag)
        except Exception:
            pass
        self._write_log("── process ended ──", "dim")

    # ── Button handlers ───────────────────────────────────
    def _on_start(self):
        if self._is_running():
            return
        
        port = self.server_port
        if self._check_port_in_use(port):
            self._write_log(f"Cannot start: Port {port} is already in use.", "err")
            self._refresh_status()
            return

        self._write_log(f"Starting server on port {port}...", "accent")
        env = os.environ.copy()
        env["YTGUI_HOST"] = "0.0.0.0"
        env["YTGUI_PORT"] = str(port)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs["preexec_fn"] = os.setsid
            
        try:
            self.process = subprocess.Popen(
                [PYTHON, "main.py"],
                cwd=str(BASE_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                errors="replace",
                encoding="utf-8",
                **kwargs
            )
            threading.Thread(target=self._pipe_stdout, daemon=True).start()
            self._write_log(f"Server process created — PID {self.process.pid}", "ok")
            
            # Start thread to poll port and show popup when server is fully ready
            threading.Thread(target=self._wait_for_server_ready, args=(port,), daemon=True).start()
        except Exception as e:
            self._write_log(f"Failed to start: {e}", "err")
            
        self._refresh_status()

    def _wait_for_server_ready(self, port: int):
        self._write_log("Waiting for server to bind and listen...", "dim")
        self._last_stdout_line = ""
        start_time = time.time()
        success = False
        last_log = start_time
        while time.time() - start_time < 120:  # wait up to 120 seconds (2 minutes)
            if not self._is_running():
                break
            if self._check_port_in_use(port):
                success = True
                break
            
            now = time.time()
            if now - last_log >= 3.0:  # print status every 3 seconds
                elapsed = int(now - start_time)
                status_info = f" -> {self._last_stdout_line}" if self._last_stdout_line else ""
                self._write_log(f"Waiting... ({elapsed}s elapsed){status_info}", "dim")
                last_log = now
                
            time.sleep(0.5)
            
        if success:
            self._write_log(f"Server is fully active and listening on port {port}!", "ok")
            self.after(0, lambda: self._show_server_ready_popup(port))
        else:
            if not self._is_running():
                self._write_log("Server process terminated unexpectedly.", "err")
            else:
                self._write_log("Server failed to respond on port in time (120s timeout).", "err")

    def _show_server_ready_popup(self, port: int):
        popup = tk.Toplevel(self)
        popup.title("Server Ready")
        popup.geometry("380x200")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        
        # Center popup relative to main window
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        popup.geometry(f"+{x}+{y}")
        
        # Title
        tk.Label(
            popup, text="🚀 Server Berhasil Dijalankan!",
            bg=BG, fg=GREEN, font=("Segoe UI", 12, "bold"),
            pady=15
        ).pack()
        
        # Message
        tk.Label(
            popup, 
            text=f"Server ytgui aktif pada port {port}.\nSilakan login untuk mengelola room.",
            bg=BG, fg=TEXT_2, font=("Segoe UI", 10),
            justify="center"
        ).pack(pady=(0, 15))
        
        # Action Buttons frame
        btn_frame = tk.Frame(popup, bg=BG)
        btn_frame.pack(pady=10)
        
        # Buka Halaman Login
        btn_login = tk.Button(
            btn_frame, text="🔑 Buka Halaman Login", bg=ACCENT, fg=BG,
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            cursor="hand2", padx=14, pady=6,
            command=lambda: [webbrowser.open(f"http://localhost:{port}/admin"), popup.destroy()]
        )
        btn_login.pack(side="left", padx=5)
        
        # Tutup button
        btn_close = tk.Button(
            btn_frame, text="Tutup", bg=BG_CARD, fg=TEXT_2,
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            cursor="hand2", padx=14, pady=6,
            command=popup.destroy
        )
        btn_close.pack(side="left", padx=5)
        
        # Hover effects
        def on_enter_login(e): btn_login.config(bg=TEXT_1)
        def on_leave_login(e): btn_login.config(bg=ACCENT)
        btn_login.bind("<Enter>", on_enter_login)
        btn_login.bind("<Leave>", on_leave_login)
        
        def on_enter_close(e): btn_close.config(bg=BORDER, fg=TEXT_1)
        def on_leave_close(e): btn_close.config(bg=BG_CARD, fg=TEXT_2)
        btn_close.bind("<Enter>", on_enter_close)
        btn_close.bind("<Leave>", on_leave_close)

    def _on_stop(self):
        if not self._is_running():
            return
        self._write_log("Stopping server...", "accent")
        try:
            self._kill_process_tree(self.process.pid)
            threading.Thread(target=self._wait_stop, daemon=True).start()
        except Exception as e:
            self._write_log(f"Error terminating: {e}", "err")

    def _wait_stop(self):
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            try:
                self.process.kill()
            except Exception:
                pass
            self._write_log("Force killed.", "err")

    def _on_restart(self):
        self._write_log("Restarting...", "accent")
        def _do():
            if self._is_running():
                try:
                    self._kill_process_tree(self.process.pid)
                    self.process.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
            time.sleep(0.8)
            self.after(0, self._on_start)
        threading.Thread(target=_do, daemon=True).start()

    def _on_open(self):
        port = self.server_port
        webbrowser.open(f"http://localhost:{port}")

    def _on_kill_conflict(self):
        pid = getattr(self, "_conflict_pid", None)
        port = self.server_port
        if not pid:
            pid = self._get_pid_occupying_port(port)
            
        if pid:
            self._write_log(f"Killing process tree using port {port} (PID {pid})...", "accent")
            self._kill_process_tree(pid)
            time.sleep(0.8)
            if not self._check_port_in_use(port):
                self._write_log(f"Port {port} successfully cleared!", "ok")
            else:
                self._write_log(f"Failed to clear port {port}.", "err")
        else:
            self._write_log(f"Cannot identify PID for port {port}.", "err")
            
        self._refresh_status()

    def _on_reset_password(self):
        # Confirm with user first
        if not messagebox.askyesno("Reset Password", "Apakah Anda yakin ingin mereset password admin? Ini akan menimpa password yang ada."):
            return
            
        try:
            # Import hash function
            try:
                from core.security import hash_password
            except ImportError:
                import hashlib
                import base64
                def hash_password(password: str) -> str:
                    salt = secrets.token_bytes(16)
                    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
                    return f"pbkdf2:sha256:100000${base64.b64encode(salt).decode('utf-8')}${base64.b64encode(key).decode('utf-8')}"
            
            raw_password = secrets.token_urlsafe(12)
            hashed_password = hash_password(raw_password)
            
            password_file = BASE_DIR / "cache" / "admin_password.txt"
            password_file.parent.mkdir(parents=True, exist_ok=True)
            with open(password_file, "w", encoding="utf-8") as f:
                f.write(hashed_password)
                
            self._show_new_password_dialog(raw_password)
            self._write_log("Admin password has been reset successfully.", "ok")
        except Exception as e:
            self._write_log(f"Error resetting password: {e}", "err")

    def _show_new_password_dialog(self, raw_password):
        dialog = tk.Toplevel(self)
        dialog.title("Password Admin Baru")
        dialog.geometry("400x240")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog relative to main window
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 240) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        tk.Label(
            dialog, text="🔑 Password Admin Berhasil Direset",
            bg=BG, fg=ACCENT, font=("Segoe UI", 12, "bold"),
            pady=10
        ).pack()
        
        # Warning
        warning_label = tk.Label(
            dialog, 
            text="Simpan password ini baik-baik!\nPassword ini tidak akan ditampilkan lagi setelah jendela ini ditutup.",
            bg=BG, fg=RED, font=("Segoe UI", 9, "italic"),
            justify="center"
        )
        warning_label.pack(pady=(0, 10))
        
        # Password entry field (read-only for easy copy)
        frame = tk.Frame(dialog, bg=BG_CARD, padx=10, pady=10, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(frame, text="Username: admin", bg=BG_CARD, fg=TEXT_2, font=("Segoe UI", 9)).pack(anchor="w")
        
        pass_frame = tk.Frame(frame, bg=BG_CARD)
        pass_frame.pack(fill="x", pady=(5, 0))
        
        entry = tk.Entry(
            pass_frame, bg=BG_SURFACE, fg=TEXT_1, 
            font=("Consolas", 11, "bold"), relief="flat",
            highlightthickness=0
        )
        entry.insert(0, raw_password)
        entry.config(state="readonly")
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        
        def copy_pass():
            self.clipboard_clear()
            self.clipboard_append(raw_password)
            btn_copy.config(text="✓ Copied", fg=GREEN)
            dialog.after(2000, lambda: btn_copy.config(text="📋 Copy", fg=TEXT_1))
            
        btn_copy = tk.Button(
            pass_frame, text="📋 Copy", bg=BG_CARD, fg=TEXT_1,
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0,
            cursor="hand2", command=copy_pass, padx=8
        )
        btn_copy.pack(side="right", padx=(5, 0))
        
        # Close button
        btn_close = tk.Button(
            dialog, text="Tutup", bg=ACCENT, fg=BG,
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
            cursor="hand2", command=dialog.destroy, padx=20, pady=5
        )
        btn_close.pack(pady=15)

    # ── Clean exit ────────────────────────────────────────
    def destroy(self):
        if self._is_running():
            try:
                self._kill_process_tree(self.process.pid)
            except Exception:
                pass
        super().destroy()

if __name__ == "__main__":
    app = ServerManager()
    app.mainloop()