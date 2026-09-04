#!/usr/bin/env python3
"""
==============================================================================
GAMA SERVER MANAGER - Quan ly vong doi cua gama-server (headless WebSocket)
==============================================================================
Khoi dong / dung gama-server bang script chinh thuc:
    bash /Applications/Gama.app/Contents/headless/gama-headless.sh -socket <PORT>

gama-server lang nghe tai ws://localhost:<PORT>, nhan cac lenh JSON
(load, step, expression, reload, ...) tu Python thong qua thu vien gama-client.
==============================================================================
"""

import os
import signal
import socket
import subprocess
import time

GAMA_HEADLESS = "/Applications/Gama.app/Contents/headless/gama-headless.sh"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.join(BASE_DIR, "run")


class GamaServerError(Exception):
    pass


class GamaServerManager:
    """Quan ly subprocess cua gama-server."""

    def __init__(self, port=6868, gama_headless=GAMA_HEADLESS,
                 workdir=None, log_file=None, startup_timeout=300.0):
        self.port = int(port)
        self.gama_headless = gama_headless
        self.workdir = workdir or os.path.join(RUN_DIR, "server_ws")
        self.log_file = log_file or os.path.join(RUN_DIR, "gama_server.log")
        self.startup_timeout = float(startup_timeout)
        self.process = None
        self._log_fh = None
        os.makedirs(self.workdir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    # ------------------------------------------------------------------ utils
    def is_port_open(self, timeout=1.0):
        """Kiem tra cong WebSocket co ai dang lang nghe khong."""
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=timeout):
                return True
        except OSError:
            return False

    def _tail_log(self, n=25):
        try:
            with open(self.log_file, "r", errors="replace") as f:
                return "".join(f.readlines()[-n:])
        except OSError:
            return "(khong doc duoc log)"

    # ----------------------------------------------------------------- start
    def start(self, reuse_running=True):
        """
        Khoi dong gama-server. Neu cong da mo va reuse_running=True thi
        gia su server van chay (khong khoi dong lai).
        Tra ve True neu da co server san sang.
        """
        if self.is_port_open():
            if reuse_running:
                print(f"[GamaServer] Cong {self.port} da mo -> dung lai server hien co.")
                return True
            raise GamaServerError(f"Cong {self.port} da bi chiem boi tien trinh khac.")

        os.makedirs(self.workdir, exist_ok=True)
        self._log_fh = open(self.log_file, "w")
        cmd = ["bash", self.gama_headless, "-socket", str(self.port)]
        print(f"[GamaServer] Dang khoi dong: {' '.join(cmd)}  (workdir={self.workdir})")
        print(f"[GamaServer] Log: {self.log_file}  (khoi dong GAMA mat ~30-90s)")
        self.process = subprocess.Popen(
            cmd, cwd=self.workdir, stdout=self._log_fh, stderr=subprocess.STDOUT,
        )

        t0 = time.time()
        while time.time() - t0 < self.startup_timeout:
            if self.process.poll() is not None:
                raise GamaServerError(
                    "gama-server ket thuc som voi code "
                    f"{self.process.returncode}. Log cuoi:\n{self._tail_log()}"
                )
            if self.is_port_open():
                print(f"[GamaServer] San sang tai ws://localhost:{self.port} "
                      f"(sau {time.time() - t0:.0f}s).")
                return True
            time.sleep(2.0)

        self.stop()
        raise GamaServerError(
            f"Timeout {self.startup_timeout}s cho gama-server mo cong {self.port}. "
            f"Log cuoi:\n{self._tail_log()}"
        )

    # ------------------------------------------------------------------ stop
    def stop(self, force=False):
        """Dung gama-server (terminate, roi kill neu can)."""
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                self.process.send_signal(signal.SIGKILL if force else signal.SIGTERM)
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
            except ProcessLookupError:
                pass
        print("[GamaServer] Da dung gama-server.")
        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None
        self.process = None

    # ----------------------------------------------------------- context mgr
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()