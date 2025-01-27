import os
from PyQt6.QtCore import QThread, pyqtSignal
from yt_dlp import YoutubeDL

class DownloadThread(QThread):
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal()
    error_signal = pyqtSignal(str)
    warning_signal = pyqtSignal(str)

    def __init__(self, download_button, operation, status, status_bar, url, selected_stream, filetype, save_path):
        super().__init__()
        self.status = status
        self.operation = operation
        self.url = url
        self.selected_stream = selected_stream
        self.filetype = filetype
        self.save_path = save_path
        self.download_button = download_button
        self.is_downloading = False

    def run(self):
        self.is_downloading = True

        # Debug: Print the structure of selected_stream to inspect its keys
        print("Selected stream data:", self.selected_stream)

        # Use .get() to avoid KeyError in case 'title' is missing
        title = self.selected_stream.get('title', 'unknown_title')
        
        # Create file name with the correct extension
        output_filename = os.path.join(self.save_path, f'{title}.{self.filetype}')

        # Check if the file already exists
        if os.path.exists(output_filename):
            self.error_signal.emit(f"Error: File '{output_filename}' already exists.")
            self.is_downloading = False
            return  # Exit the download process

        # yt-dlp options
        ydl_opts = {
            'format': self.selected_stream['format_id'],
            'outtmpl': os.path.join(self.save_path, f'%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.filetype,
                'preferredquality': '192',
            }],
            'progress_hooks': [self.progress_hook],
            'rm_cache_dir': True,  # Automatically delete the cache directory
        }

        self.operation.setText("Downloading...")
        self.status.setText("Downloading...")

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.download_finished.emit()
        except Exception as e:
            self.error_signal.emit(f"An error occurred: {e}")
        finally:
            self.is_downloading = False

    def progress_hook(self, progress):
        if progress['status'] == 'downloading':
            total_bytes = progress.get('total_bytes')
            downloaded_bytes = progress.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                percent = int(downloaded_bytes / total_bytes * 100)
                self.download_progress.emit(percent)
