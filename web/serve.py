"""
Dev server with live reload.

Usage: python web/serve.py
Serves web/ on http://localhost:8000 with auto-reload on file changes.
"""

import subprocess
from pathlib import Path
from livereload import Server

WEB = Path(__file__).parent


def rebuild():
    subprocess.run(['python', str(WEB / 'build.py')])


server = Server()
server.watch(str(WEB / 'copy/*.md'), rebuild)
server.watch(str(WEB / 'template.html'), rebuild)
server.watch(str(WEB / '*.js'))
server.watch(str(WEB / 'style.css'))
server.serve(root=str(WEB), port=8000)
