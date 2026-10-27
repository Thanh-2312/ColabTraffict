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
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections import deque

GAMA_HEADLESS_DEFAULT = "/Applications/Gama.app/Contents/headless/gama-headless.sh"


def is_x11_server_running(display=":99"):
    """Kiem tra xem X11 server co dang chap nhan ket noi qua UNIX socket hay khong."""
    if not sys.platform.startswith("linux"):
        return True
    display_num = display.lstrip(":").split(".")[0]
    sock_path = f"/tmp/.X11-unix/X{display_num}"
    if not os.path.exists(sock_path):
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(sock_path)
        s.close()
        return True
    except Exception:
        return False


def ensure_xvfb_running(display=":99"):
    """
    Bao dam luon co 1 tien trinh Xvfb hoat dong on dinh tren display duoc chi dinh.
    Tu dong don dep lock file chet va khoi dong Xvfb an toan (tat GLX gay crash Mesa).
    """
    if not sys.platform.startswith("linux"):
        return True

    if is_x11_server_running(display):
        return True

    display_num = display.lstrip(":").split(".")[0]
    lock_file = f"/tmp/.X{display_num}-lock"
    sock_path = f"/tmp/.X11-unix/X{display_num}"

    # Don dep stale locks
    for p in [lock_file, sock_path]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    xvfb_bin = shutil.which("Xvfb")
    if not xvfb_bin:
        print(f"[GamaServer] Canh bao: Khong tim thay Xvfb trong he thong!")
        return False

    cmd = [
        xvfb_bin, display,
        "-screen", "0", "1024x768x24",
        "-ac",
        "-extension", "GLX",
        "+render",
        "-noreset"
    ]
    print(f"[GamaServer] Tu dong khoi dong Xvfb tren {display} (cmd: {' '.join(cmd)})...")
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as ex:
        print(f"[GamaServer] Loi khi spawn Xvfb: {ex}")
        return False

    t_end = time.time() + 5.0
    while time.time() < t_end:
        if is_x11_server_running(display):
            print(f"[GamaServer] Xvfb tren {display} da san sang!")
            return True
        time.sleep(0.2)

    print(f"[GamaServer] Canh bao: Xvfb tren {display} chua phan hoi sau 5s.")
    return False


def find_gama_headless(custom_path=None):
    candidates = [
        custom_path,
        os.environ.get("GAMA_HEADLESS"),
        os.path.expanduser(r"~\AppData\Local\Programs\Gama\headless\gama-headless.bat"),
        r"C:\Program Files\Gama\headless\gama-headless.bat",
        r"C:\Program Files (x86)\Gama\headless\gama-headless.bat",
        r"C:\Gama\headless\gama-headless.bat",
        "/opt/gama-platform/headless/gama-headless.sh",
        "/opt/gama/headless/gama-headless.sh",
        "/content/gama/headless/gama-headless.sh",
        "/usr/lib/gama/headless/gama-headless.sh",
        GAMA_HEADLESS_DEFAULT,
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    # Search recursively in AppData or /opt
    if sys.platform == "win32":
        appdata_local = os.path.expanduser(r"~\AppData\Local\Programs")
        if os.path.exists(appdata_local):
            for root, _, files in os.walk(appdata_local):
                if "gama-headless.bat" in files:
                    return os.path.join(root, "gama-headless.bat")
    elif os.path.exists("/opt"):
        for root, _, files in os.walk("/opt"):
            if "gama-headless.sh" in files:
                return os.path.join(root, "gama-headless.sh")
    return custom_path or os.environ.get("GAMA_HEADLESS", GAMA_HEADLESS_DEFAULT)


GAMA_HEADLESS = find_gama_headless()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.join(BASE_DIR, "run")


class GamaServerError(Exception):
    pass


class GamaServerManager:
    """Quan ly subprocess cua gama-server."""

    def __init__(self, port=6868, gama_headless=None,
                 workdir=None, log_file=None, startup_timeout=300.0):
        self.port = int(port)
        self.gama_headless = find_gama_headless(gama_headless)
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
                return "".join(deque(f, maxlen=n))
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
                print(
                    f"[GamaServer] Cong {self.port} da mo -> dung lai server hien co.")
                return True
            raise GamaServerError(
                f"Cong {self.port} da bi chiem boi tien trinh khac.")

        os.makedirs(self.workdir, exist_ok=True)
        self._log_fh = open(self.log_file, "w")
        configuration = os.path.join(self.workdir, "configuration")
        workspace = os.path.join(self.workdir, "workspace")
        os.makedirs(workspace, exist_ok=True)
        if not self.gama_headless or not os.path.isfile(self.gama_headless):
            self.gama_headless = find_gama_headless(self.gama_headless)
        if not self.gama_headless or not os.path.isfile(self.gama_headless):
            raise GamaServerError(
                f"Không tìm thấy file gama-headless tại: '{self.gama_headless}'.\n"
                "👉 Trên Google Colab: Nếu session vừa được restart hoặc ngắt kết nối, "
                "thư mục /opt/ sẽ bị xóa. Hãy chạy lại ô lệnh ở BƯỚC 3 trong notebook để cài đặt GAMA!"
            )
        if sys.platform == "win32":
            cmd = ["cmd.exe", "/c", self.gama_headless, "-socket", str(self.port),
                   "-configuration", configuration, "-data", workspace]
            exec_cwd = os.path.dirname(self.gama_headless)
        else:
            cmd = ["bash", self.gama_headless, "-socket", str(self.port),
                   "-configuration", configuration, "-data", workspace]
            exec_cwd = self.workdir

        print(
            f"[GamaServer] Dang khoi dong: {' '.join(cmd)}  (cwd={exec_cwd})")
        print(
            f"[GamaServer] Log: {self.log_file}  (khoi dong GAMA mat ~30-90s)")
        # Dam bao Xvfb dang hoat dong truoc khi start GAMA tren Linux
        target_display = os.environ.get("DISPLAY") or ":99"
        if sys.platform.startswith("linux") and not is_x11_server_running(target_display):
            ensure_xvfb_running(":99")
            target_display = ":99"
            os.environ["DISPLAY"] = ":99"

        env = os.environ.copy()
        if sys.platform.startswith("linux"):
            env["DISPLAY"] = target_display
            env["LIBGL_ALWAYS_SOFTWARE"] = "1"
            env["LIBGL_DRI3_DISABLE"] = "1"
            env["LIBGL_DRI2_DISABLE"] = "1"
            env["GALLIUM_DRIVER"] = "llvmpipe"
            env["MESA_LOADER_DRIVER_OVERRIDE"] = "llvmpipe"
            env["__GLX_VENDOR_LIBRARY_NAME"] = "mesa"
            env["LIBGL_ALWAYS_INDIRECT"] = "0"
            env["GDK_BACKEND"] = "x11"
            env["NO_AT_BRIDGE"] = "1"

            # Ngăn JVM AWT/SWT gọi hàm OpenGL bị crash trên Xvfb
            java_opts = env.get("_JAVA_OPTIONS", "")
            extra_opts = [
                "-Dsun.java2d.opengl=false",
                "-Dsun.java2d.xrender=false",
                "-Djava.awt.headless=false",
            ]
            for opt in extra_opts:
                if opt.split("=")[0] not in java_opts:
                    java_opts = (java_opts + " " + opt).strip()
            env["_JAVA_OPTIONS"] = java_opts

        self.process = subprocess.Popen(
            cmd, cwd=exec_cwd, stdout=self._log_fh, stderr=subprocess.STDOUT,
            start_new_session=True, env=env,
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
        if self.process is not None:
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True, check=False
                    )
                except Exception:
                    pass
            else:
                try:
                    os.killpg(self.process.pid,
                              signal.SIGKILL if force else signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
            deadline = time.monotonic() + (2 if force else 15)
            while time.monotonic() < deadline:
                if self.process.poll() is not None and not self.is_port_open(timeout=.1):
                    break
                time.sleep(0.1)
            else:
                if sys.platform == "win32":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                            capture_output=True, check=False
                        )
                    except Exception:
                        pass
                else:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            self.process.wait(timeout=10)
            deadline = time.monotonic() + 10
            while self.is_port_open(timeout=.1):
                if time.monotonic() >= deadline:
                    raise GamaServerError(
                        f"Cong {self.port} van mo sau khi dung server da tao.")
                time.sleep(.1)
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
