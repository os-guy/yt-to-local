import sys
import os
import traceback
import subprocess
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLineEdit, QLabel, QComboBox, QFileDialog, QWidget, QMessageBox, QProgressBar, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRunnable, QThreadPool
from yt_dlp import YoutubeDL
import re
import shutil

class URLFinder(QRunnable):
    def __init__(self, url_input, quality_combo, filetype_combo, download_button, choose_folder_button, choose_folder_status, quality_label, filetype_label, status_bar):
        super().__init__()
        self.url_input = url_input
        self.quality_combo = quality_combo
        self.filetype_combo = filetype_combo
        self.download_button = download_button
        self.choose_folder_button = choose_folder_button
        self.choose_folder_status = choose_folder_status
        self.quality_label = quality_label
        self.filetype_label = filetype_label
        self.status_bar = status_bar

    def run(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_bar.showMessage("Please enter a YouTube URL")
            return

        try:
            self.status_bar.showMessage("Finding URL...")
            ydl_opts = {'quiet': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_streams = [stream for stream in info['formats'] if 'acodec' in stream and stream['acodec'] != 'none']

            if audio_streams:
                self.status_bar.showMessage("URL found")
                self.quality_label.setVisible(True)  # Show quality selection title
                self.quality_combo.setVisible(True)  # Show quality selection section
                self.filetype_label.setVisible(True)  # Show filetype selection title
                self.filetype_combo.setVisible(True)  # Show filetype selection section
                self.download_button.setVisible(True)  # Show download button
                self.choose_folder_button.setVisible(True)  # Show choose folder button
                self.choose_folder_status.setText("Folder Not Selected")

                # Populate quality combo box
                audio_streams = sorted(audio_streams, key=lambda x: float(x['abr']) if 'abr' in x and isinstance(x['abr'], str) else float('inf'))
                for stream in reversed(audio_streams):
                    quality_info = f"{stream['abr']} kbps" if 'abr' in stream else 'Variable bitrate'
                    self.quality_combo.addItem(quality_info, stream)

                # Populate filetype combo box
                filetypes = ['mp3', 'wav', 'flac']  # Add more filetypes if needed
                self.filetype_combo.addItems(filetypes)

            else:
                self.status_bar.showMessage("No audio streams found")
                self.quality_label.setVisible(False)  # Hide quality selection title
                self.quality_combo.setVisible(False)  # Hide quality selection section
                self.filetype_label.setVisible(False)  # Hide filetype selection title
                self.filetype_combo.setVisible(False)  # Hide filetype selection section
                self.download_button.setVisible(False)  # Hide download button
                self.choose_folder_button.setVisible(False)  # Hide choose folder button
                self.choose_folder_status.setText("Folder Not Selected")

        except Exception as e:
            self.status_bar.showMessage("Error: " + str(e))

# Worker thread class for downloading
class DownloadThread(QThread):
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal()

    def __init__(self, url, selected_stream, filetype, save_path, video_title):
        super().__init__()
        self.url = url
        self.selected_stream = selected_stream
        self.filetype = filetype
        self.save_path = save_path
        self.video_title = video_title

    def run(self):
        try:
            # Check if the file already exists
            if os.path.exists(os.path.join(self.save_path, f"{self.video_title}.{self.filetype}")):
                QMessageBox.warning(None, "Warning", "File already exists.")
                return
            
            ffmpeg_path = shutil.which('ffmpeg')
            ffprobe_path = shutil.which('ffprobe')

            if ffmpeg_path and ffprobe_path:
                ydl_opts = {
                    'format': self.selected_stream['format_id'],
                    'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                    'quiet': False,  # Show download progress
                    'progress_hooks': [self.progress_hook],
                    'ffmpeg_location': ffmpeg_path,  # Use the found ffmpeg path
                    'ffprobe_location': ffprobe_path,  # Use the found ffprobe path
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': self.filetype,
                }],
            }
            else:
                print("ffmpeg or ffprobe not found in PATH")
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.download_finished.emit()  # Emit signal when download finishes
        except Exception as e:
            print(f"Error occurred: {e}")
            self.download_progress.emit(0)

    def progress_hook(self, progress):
        if progress['status'] == 'downloading':
            total_bytes = progress.get('total_bytes')
            downloaded_bytes = progress.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                percent = int(downloaded_bytes / total_bytes * 100)
                self.download_progress.emit(percent)

# Main window class
class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.save_path = None
        self.statusBar().showMessage("Ready")
        self.setFixedSize(600,350)

        self.label_url = QLabel('YouTube URL:', self)
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL here")
        self.find_button = QPushButton('Find', self)
        self.label_quality = QLabel('Select Audio Quality:', self)
        self.quality_combo = QComboBox(self)
        self.quality_combo.setVisible(False)  # Initially hidden
        self.label_filetype = QLabel('Select File Type:', self)
        self.filetype_combo = QComboBox(self)
        self.filetype_combo.setVisible(False)  # Initially hidden
        self.download_button = QPushButton('Download', self)
        self.download_button.setVisible(False)  # Initially hidden
        self.open_folder_button = QPushButton('Open Folder', self)
        self.choose_folder_button = QPushButton('Choose Folder', self)
        self.choose_folder_status = QLabel("Folder Not Selected", self)
        self.choose_folder_button.setVisible(False)  # Initially hidden
        self.open_folder_button.setVisible(False)  # Initially hidden

        layout = QVBoxLayout()
        layout.addWidget(self.label_url)
        layout.addWidget(self.url_input)
        layout.addWidget(self.find_button)
        layout.addWidget(self.label_quality)
        layout.addWidget(self.quality_combo)
        layout.addWidget(self.label_filetype)
        layout.addWidget(self.filetype_combo)
        layout.addWidget(self.download_button)
        layout.addWidget(self.open_folder_button)
        layout.addWidget(self.choose_folder_button)
        layout.addWidget(self.choose_folder_status)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.find_button.clicked.connect(self.find_video)
        self.download_button.clicked.connect(self.download)
        self.open_folder_button.clicked.connect(self.open_folder)
        self.choose_folder_button.clicked.connect(self.choose_folder)

        self.label_quality.setVisible(False)
        self.label_filetype.setVisible(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.statusBar().addPermanentWidget(self.progress_bar)
    
    def update_download_progress(self, progress):
        print("Progress received:", progress)  # Debugging
        self.progress_bar.setValue(progress)
        if progress == 100:
            self.download_finished()

    def download_finished(self):
        print("Download finished")
        self.statusBar().showMessage("Download finished")
        self.show_open_folder_button()
    
    def find_video(self):
        url_finder = URLFinder(self.url_input, self.quality_combo, self.filetype_combo, self.download_button, self.choose_folder_button, self.choose_folder_status, self.label_quality, self.label_filetype, self.statusBar())
        QThreadPool.globalInstance().start(url_finder)
        self.quality_combo.setVisible(False)  # Hide quality selection section while finding URL
        self.filetype_combo.setVisible(False)  # Hide filetype selection section while finding URL
        self.download_button.setVisible(False)  # Hide download button while finding URL
        self.label_quality.setVisible(False)  # Hide quality selection title while finding URL
        self.label_filetype.setVisible(False)  # Hide filetype selection title while finding URL
        self.choose_folder_button.setVisible(False)  # Hide choose folder button while finding URL
        self.open_folder_button.setVisible(False)
        self.choose_folder_status.setText("Folder Not Selected")  # Reset folder status

    def download(self):
        url = self.url_input.text().strip()
        if not url:
            self.statusBar().showMessage("Please enter a YouTube URL")
            return

        if not self.save_path:
            QMessageBox.critical(self, "Error", "Please choose a save path.")
            return

        if self.quality_combo.currentIndex() == -1:
            QMessageBox.critical(self, "Error", "Please select the quality.")
            return

        try:
            # Fetch video information
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')

            selected_stream = self.quality_combo.currentData()
            if selected_stream:
                self.statusBar().showMessage("Downloading...")

                # Define filetype
                filetype = self.filetype_combo.currentText()

                self.download_thread = DownloadThread(url, selected_stream, filetype, self.save_path, video_title)
                self.download_thread.download_progress.connect(self.update_download_progress)
                self.download_thread.download_finished.connect(self.download_finished)  # Connect to download finished slot
                self.download_thread.start()

        except Exception as e:
            print(f"Error occurred: {e}")
            self.statusBar().showMessage("Error: " + str(e))

    def choose_folder(self):
        self.save_path = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if self.save_path:
            self.choose_folder_status.setText("Folder Selected")
        else:
            self.choose_folder_status.setText("Folder Not Selected")

    def open_folder(self):
        if self.save_path:
            if sys.platform == 'win32':
                os.startfile(self.save_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.save_path])
            else:
                subprocess.Popen(['xdg-open', self.save_path])

    def show_open_folder_button(self):
        self.open_folder_button.setVisible(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    sys.exit(app.exec())
