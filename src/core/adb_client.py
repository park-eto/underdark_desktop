import os
import sys
import shutil
import time
import cv2
import numpy as np
from typing import Optional, List, Tuple
from adbutils import adb, AdbDevice


def _configure_adb_environment() -> None:
    """
    PyInstaller 단일 실행파일(_MEIxxxxxx 임시 폴더) 환경에서 매 실행마다 새로운 경로의 adb.exe가
    실행되어 Windows 방화벽(UAC 관리자 권한 창)이 반복 팝업되는 현상 및 LDPlayer 내장 ADB와의
    버전 충돌(v34 vs v36)로 인한 서버 재시작 현상을 방지하기 위해 고정된 adb.exe 경로와
    로컬 전용 환경변수를 설정합니다.
    """
    # 1. ADB v36+의 mDNS(무선 디버깅 UDP 멀티캐스트 탐색) 비활성화 -> 방화벽 팝업 유발 원천 차단
    os.environ["ADB_MDNS"] = "0"
    os.environ["ADB_MDNS_OPENSCREEN"] = "0"
    os.environ["ADB_MDNS_AUTO_CONNECT"] = ""

    if os.environ.get("ADBUTILS_ADB_PATH") and os.path.isfile(os.environ["ADBUTILS_ADB_PATH"]):
        return

    # 2. LDPlayer 자체 adb.exe 탐색 (버전 충돌 방지 및 고정 경로 사용)
    candidate_paths: List[str] = []
    if os.name == "nt":
        try:
            import winreg
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for subkey in (
                    r"Software\XuanZhi\LDPlayer9",
                    r"Software\XuanZhi\LDPlayer4",
                    r"Software\leidian\ldplayer9",
                ):
                    try:
                        with winreg.OpenKey(root, subkey) as k:
                            install_dir, _ = winreg.QueryValueEx(k, "InstallDir")
                            if install_dir:
                                candidate_paths.append(os.path.join(str(install_dir), "adb.exe"))
                    except OSError:
                        pass
        except Exception:
            pass

        candidate_paths.extend([
            r"C:\LDPlayer\LDPlayer9\adb.exe",
            r"D:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\LDPlayer\LDPlayer4.0\adb.exe",
            r"D:\LDPlayer\LDPlayer4.0\adb.exe",
        ])
    elif sys.platform == "darwin":
        # macOS (Apple Silicon / Intel) + BlueStacks Air 용 adb 탐색
        which_adb = shutil.which("adb")
        if which_adb:
            candidate_paths.append(which_adb)
        candidate_paths.extend([
            "/opt/homebrew/bin/adb",
            "/usr/local/bin/adb",
            os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
            "/Applications/BlueStacks.app/Contents/MacOS/hd-adb",
        ])

    for path in candidate_paths:
        if path and os.path.isfile(path):
            os.environ["ADBUTILS_ADB_PATH"] = path
            return

    # 3. LDPlayer 기본 경로가 없을 경우, PyInstaller 임시 폴더(_MEIxxxxxx) 대신
    #    고정된 AppData 경로(%LOCALAPPDATA%\UnderdarkMacroSolver\adb)로 바이너리 복사 후 사용
    try:
        from adbutils._utils import _get_bin_dir
        src_bin_dir = _get_bin_dir()
        src_adb = os.path.join(src_bin_dir, "adb.exe" if os.name == "nt" else "adb")
        if os.path.isfile(src_adb):
            local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            fixed_bin_dir = os.path.join(local_appdata, "UnderdarkMacroSolver", "adb")
            os.makedirs(fixed_bin_dir, exist_ok=True)
            fixed_adb = os.path.join(fixed_bin_dir, os.path.basename(src_adb))

            for fname in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "adb"):
                s_file = os.path.join(src_bin_dir, fname)
                d_file = os.path.join(fixed_bin_dir, fname)
                if os.path.isfile(s_file) and not os.path.isfile(d_file):
                    shutil.copy2(s_file, d_file)

            if os.path.isfile(fixed_adb):
                os.environ["ADBUTILS_ADB_PATH"] = fixed_adb
    except Exception:
        pass


_configure_adb_environment()


class AdbClient:
    """
    LDPlayer 및 안드로이드 에뮬레이터 연결 및 제어를 담당하는 클래스.
    """
    def __init__(self, serial: Optional[str] = None):
        _configure_adb_environment()
        self.serial = serial
        self.device: Optional[AdbDevice] = None
        self.is_connected = False

    def list_devices(self) -> List[str]:
        """연결 가능한 ADB 디바이스 시리얼 목록 반환"""
        try:
            devices = adb.device_list()
            return [d.serial for d in devices]
        except Exception as e:
            print(f"[ADB] 디바이스 목록 조회 실패: {e}")
            return []

    def connect(self, serial: Optional[str] = None) -> bool:
        """
        ADB 디바이스에 연결.
        serial이 없으면 기본 LDPlayer 포트(127.0.0.1:5555 등)를 자동 스캔하거나 첫 번째 디바이스에 연결.
        """
        try:
            if serial:
                self.serial = serial
            
            # 지정된 시리얼이 없으면 일반적인 LDPlayer 포트 연결 시도
            if not self.serial:
                devices = self.list_devices()
                if devices:
                    self.serial = devices[0]
                else:
                    # 포트 수동 연결 시도 (LDPlayer & BlueStacks Air 기본 5555, 5556, 5557 등)
                    for port in [5555, 5556, 5557, 5559, 5587]:
                        try:
                            adb.connect(f"127.0.0.1:{port}")
                        except Exception:
                            pass
                    devices = self.list_devices()
                    if devices:
                        self.serial = devices[0]

            if not self.serial:
                self.is_connected = False
                return False

            self.device = adb.device(self.serial)
            self.is_connected = True
            print(f"[ADB] 디바이스 연결 성공: {self.serial}")
            return True
        except Exception as e:
            print(f"[ADB] 연결 실패: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        self.device = None
        self.is_connected = False

    def capture_screen(self) -> Optional[np.ndarray]:
        """
        ADB 스크린샷을 가져와 OpenCV BGR ndarray로 반환.
        (PIL 이미지 및 바이트 버퍼 즉시 해제로 메모리 누수 방지)
        """
        if not self.is_connected or not self.device:
            return None
        try:
            # adbutils의 screenshot()은 PIL.Image.Image 객체 반환
            pil_img = self.device.screenshot()
            if pil_img is None:
                return None
            rgb_arr = np.array(pil_img)
            try:
                pil_img.close()
            except Exception:
                pass
            del pil_img

            # RGB -> BGR 변환
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            del rgb_arr
            return bgr_arr
        except Exception as e:
            # 1차 실패 시 shell screencap 폴백 시도
            try:
                raw_bytes = self.device.shell("screencap -p", encoding=None)
                if raw_bytes:
                    # Windows 개행 문자(\r\n -> \n) 정규화
                    raw_bytes = raw_bytes.replace(b"\r\n", b"\n")
                    img = cv2.imdecode(np.frombuffer(raw_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                    del raw_bytes
                    if img is not None:
                        return img
            except Exception:
                pass
            print(f"[ADB] 화면 캡처 실패: {e}")
            return None

    def tap(self, x: int, y: int):
        """
        터치 좌표로 input tap / click 전송
        """
        if not self.is_connected or not self.device:
            return
        try:
            if hasattr(self.device, "click"):
                self.device.click(x, y)
            else:
                self.device.shell(f"input tap {x} {y}")
        except Exception as e:
            print(f"[ADB] 터치 전송 실패 ({x}, {y}): {e}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 350):
        """
        드래그/스와이프 제스처 전송 (화면 스크롤 등)
        """
        if not self.is_connected or not self.device:
            return
        try:
            if hasattr(self.device, "swipe"):
                self.device.swipe(x1, y1, x2, y2, duration_ms / 1000.0)
            else:
                self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        except Exception as e:
            print(f"[ADB] 스와이프 전송 실패 ({x1},{y1} -> {x2},{y2}): {e}")

    def keyevent(self, keycode: int | str):
        """
        안드로이드 키이벤트 전송 (예: 51=W, 29=A, 47=S, 32=D)
        """
        if not self.is_connected or not self.device:
            return
        try:
            if hasattr(self.device, "keyevent"):
                self.device.keyevent(str(keycode))
            else:
                self.device.shell(f"input keyevent {keycode}")
        except Exception as e:
            print(f"[ADB] 키이벤트 전송 실패 ({keycode}): {e}")

    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """화면 해상도 (width, height) 반환"""
        if not self.is_connected or not self.device:
            return None
        try:
            w, h = self.device.window_size()
            return w, h
        except Exception:
            img = self.capture_screen()
            if img is not None:
                h, w, _ = img.shape
                return w, h
            return None
