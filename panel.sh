#!/usr/bin/env bash
# ===========================================================================
#  Turbo EA - control panel (macOS / Linux)
#
#  Opens a desktop window that runs the backend and the frontend: live logs,
#  ports, start / stop / restart, keep running, and a Settings dialog that
#  edits backend/.env. Closing the window stops both apps.
#
#  Needs a JDK 17+, Python 3.12+ and Node 20+ on PATH, and a PostgreSQL the
#  backend can reach. See tools/control-panel/README.md.
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"
command -v javac >/dev/null 2>&1 || { echo "  [X] javac not found on PATH. Install a JDK 17+."; exit 1; }
command -v node >/dev/null 2>&1 || echo "  [!] Node.js not found on PATH. The backend will run; the frontend will not."

out=tools/control-panel/.runtime/classes
javac --release 17 -encoding UTF-8 -d "$out" tools/control-panel/ControlPanel.java
nohup java -cp "$out" ControlPanel "$PWD" >/dev/null 2>&1 &
