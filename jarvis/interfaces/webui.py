"""
jarvis.interfaces.webui
=======================
Cinematic web UI for Jarvis — local Flask server serving a HUD-style
interface (animated arc reactor, activity feed, AI thinking trace,
memory & system meters). Voice wake word auto-launches it in the browser.
"""

from __future__ import annotations

import glob
import os
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory


class WebUI:
    def __init__(self, jarvis, host: str = "0.0.0.0", port: int = 8765):
        self.jarvis = jarvis
        self.host = host
        self.port = port
        self.started_at = datetime.now()
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "static")
        self.app = Flask(__name__, static_folder=static_dir,
                         static_url_path="")
        self._routes()

    # ------------------------------------------------------------------
    def _routes(self) -> None:
        app, j = self.app, self.jarvis

        @app.route("/")
        def index():
            return send_from_directory(app.static_folder, "index.html")

        @app.route("/api/status")
        def status():
            return jsonify({
                "brain": j.brain.available(),
                "activity_count": j.activity.count(),
                "uptime": int((datetime.now() - self.started_at).total_seconds()),
                "started": self.started_at.isoformat(timespec="seconds"),
            })

        @app.route("/api/activity")
        def activity():
            return jsonify(j.activity.recent(50))

        @app.route("/api/thinking")
        def thinking():
            return jsonify(j.last_thinking)

        @app.route("/api/memory")
        def memory():
            mem = j.memory
            turns = 0
            if os.path.exists(mem.path):
                with open(mem.path, encoding="utf-8") as f:
                    turns = sum(1 for _ in f)
            notes = len(glob.glob(os.path.join(mem.dir, "notes", "*.md")))
            size_kb = os.path.getsize(mem.path) / 1024 if os.path.exists(mem.path) else 0.0
            return jsonify({
                "conversation_turns": turns,
                "notes": notes,
                "profile_facts": len(mem.profile.get("facts", [])),
                "memory_kb": round(size_kb, 1),
            })

        @app.route("/api/system")
        def system():
            import psutil
            vm = psutil.virtual_memory()
            try:
                disk = psutil.disk_usage("/")
                disk_pct, disk_gb = disk.percent, round(disk.total / (1024**3), 1)
            except Exception:
                disk_pct, disk_gb = 0, 0
            return jsonify({
                "cpu": psutil.cpu_percent(interval=0.3),
                "ram_pct": vm.percent,
                "ram_gb": round(vm.total / (1024**3), 1),
                "disk_pct": disk_pct,
                "disk_gb": disk_gb,
            })

        @app.route("/api/command", methods=["POST"])
        def command():
            data = request.get_json(silent=True) or {}
            text = (data.get("text") or "").strip()
            if not text:
                return jsonify({"error": "empty command"}), 400
            reply = j.handle(text)
            return jsonify({"reply": reply, "thinking": j.last_thinking})

    # ------------------------------------------------------------------
    def run(self, open_browser: bool = True) -> None:
        url = f"http://localhost:{self.port}/"
        print(f"🖥️  Jarvis web UI: {url}")
        print(f"    Local network: http://{self.host}:{self.port}/")
        if open_browser:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass
        self.app.run(host=self.host, port=self.port,
                     threaded=True, use_reloader=False)
