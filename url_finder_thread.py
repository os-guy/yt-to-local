from PyQt6.QtCore import QThread, pyqtSignal
from yt_dlp import YoutubeDL

class URLFinderThread(QThread):
    found_url = pyqtSignal(bool)

    def __init__(self, url_input, status_bar):
        super().__init__()
        self.url_input = url_input
        self.status_bar = status_bar

    def run(self):
        url = self.url_input.toPlainText().strip()
        if not url:
            self.status_bar.showMessage("Please enter a YouTube URL")
            self.found_url.emit(False)
            return

        self.ydl_opts = {'quiet': True, 'socket_timeout': 15}
        self.ydl = YoutubeDL(self.ydl_opts)
        self.info = None
        try:
            self.status_bar.showMessage("Waiting for yt-dlp response...")  # New message when yt-dlp starts
            self.info = self.ydl.extract_info(url, download=False)
        except YoutubeDL.utils.DownloadError as e:
            print(f"Download error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            self.found_url.emit(self.info is not None)
