import os
import sys
import json
import pygame
import urllib.request
import threading
import subprocess

class GameUpdater:
    def __init__(self, current_version="v1.3.3", repo_owner="RaccoonKa", repo_name="Velaris"):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name

        self.status = "idle"
        self.latest_version = None
        self.download_url = None
        self.download_progress = 0.0
        self.downloaded_file_path = None
        self.error_message = None
        self.target_asset_name = None

    def is_no_admin_install(self):
        try:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            exe_dir = os.path.dirname(exe_path).lower()
            local_app_data = os.environ.get("LOCALAPPDATA", "").lower()
            app_data = os.environ.get("APPDATA", "").lower()

            if local_app_data and local_app_data in exe_dir:
                return True
            if app_data and app_data in exe_dir:
                return True
            if "program files" not in exe_dir:
                return True
            return False
        except Exception:
            return False

    def _parse_version(self, v_str):
        clean = v_str.lstrip('vV').strip()
        parts = []
        for p in clean.split('.'):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return parts

    def check_for_updates_async(self, on_finish=None):
        def _worker():
            self.status = "checking"
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "Velaris-Game-Client"})
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        tag = data.get("tag_name", "")
                        self.latest_version = tag

                        if self._parse_version(tag) > self._parse_version(self.current_version):
                            assets = data.get("assets", [])
                            wants_na = self.is_no_admin_install()
                            chosen_asset = None

                            if wants_na:
                                for a in assets:
                                    if "_na" in a.get("name", "").lower() and a.get("name", "").endswith(".exe"):
                                        chosen_asset = a
                                        break
                            else:
                                for a in assets:
                                    name = a.get("name", "").lower()
                                    if "_na" not in name and name.endswith(".exe"):
                                        chosen_asset = a
                                        break

                            if not chosen_asset and assets:
                                for a in assets:
                                    if a.get("name", "").endswith(".exe"):
                                        chosen_asset = a
                                        break

                            if chosen_asset:
                                self.download_url = chosen_asset.get("browser_download_url")
                                self.target_asset_name = chosen_asset.get("name")
                                self.status = "available"
                            else:
                                self.status = "no_update"
                        else:
                            self.status = "no_update"
                    else:
                        self.status = "error"
                        self.error_message = f"HTTP {response.status}"
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)

            if on_finish:
                on_finish(self.status)

        threading.Thread(target=_worker, daemon=True).start()

    def download_and_install_async(self, on_progress=None, on_ready=None):
        if not self.download_url:
            return

        def _worker():
            self.status = "downloading"
            self.download_progress = 0.0
            temp_dir = os.environ.get("TEMP", os.path.dirname(os.path.abspath(__file__)))
            file_name = self.target_asset_name or "Velaris_Update.exe"
            save_path = os.path.join(temp_dir, file_name)

            req = urllib.request.Request(self.download_url, headers={"User-Agent": "Velaris-Game-Client"})
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    total_size = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    block_size = 65536

                    with open(save_path, "wb") as f:
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            f.write(buffer)
                            downloaded += len(buffer)
                            if total_size > 0:
                                self.download_progress = downloaded / total_size
                            if on_progress:
                                on_progress(self.download_progress)

                self.downloaded_file_path = save_path
                self.status = "ready"
                if on_ready:
                    on_ready(save_path)
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)

        threading.Thread(target=_worker, daemon=True).start()

    def launch_installer_and_exit(self):
        if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
            try:
                subprocess.Popen([self.downloaded_file_path], shell=True)
                pygame.quit()
                sys.exit(0)
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)

updater = GameUpdater(current_version="v1.3.3", repo_owner="RaccoonKa", repo_name="Velaris")
