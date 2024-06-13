# For Linux

import sys
import os
import subprocess
import traceback
from PyQt6 import uic
from PyQt6.QtWidgets import QTextEdit, QApplication, QCheckBox, QMainWindow, QMessageBox, QFileDialog, QProgressBar, QPushButton, QLabel, QComboBox, QLineEdit
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QRunnable, QThreadPool
from yt_dlp import YoutubeDL

class URLFinder(QObject,QRunnable):
    video_info_found = pyqtSignal(dict)
    
    def __init__(self, open_folder, choosen_quality, choosen_filetype, status, operation, quality_combo, filetype_combo, url_input, download_button, choose_folder_button, choosen_folder_status, quality_label, filetype_label, status_bar):
        super().__init__()

        self.url_input = url_input
        self.download_button = download_button
        self.choose_folder_button = choose_folder_button
        self.choosen_folder_status = choosen_folder_status
        self.quality_label = quality_label
        self.filetype_label = filetype_label
        self.status_bar = status_bar
        self.status = status
        self.operation = operation
        self.filetype_combo = filetype_combo
        self.quality_combo = quality_combo
        self.choosen_label_quality_text = choosen_quality
        self.choosen_label_filetype_text = choosen_filetype
        self.open_folder_button = open_folder

    def run(self):
        self.hide_l_and_b()
        url = self.url_input.toPlainText().strip()

        if not url.startswith(("http://", "https://")):
            self.status_bar.showMessage("Invalid URL: Must start with http:// or https://")
            return
        if "youtube.com" not in url or "youtu.be" not in url:
            self.status_bar.showMessage("Invalid URL: Not a YouTube URL")
            return

        try:
            self.operation.setText("Finding URL...")
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
                self.video_info_found.emit(info)
                self.choosen_folder_status.setText("Folder Not Selected")
                self.status.setText("Ready")
                self.operation.setText("No Op.")
                self.status_bar.showMessage("URL Found")

                # Populate quality combo box
                self.quality_combo.clear()
                audio_streams = sorted(audio_streams, key=lambda x: float(x['abr']) if 'abr' in x and isinstance(x['abr'], str) else float('inf'))
                for stream in reversed(audio_streams):
                    if 'abr' in stream and stream['abr']:  # Ensure 'abr' exists and is not None
                        quality_info = f"{stream['abr']} kbps"
                        self.quality_combo.addItem(quality_info, stream)

                # Populate filetype combo box
                filetypes = ['mp3', 'wav', 'flac']  # Add more filetypes if needed
                self.filetype_combo.clear()
                self.filetype_combo.addItems(filetypes)
            
            else:
                self.status_bar.showMessage("No audio streams found")
                self.quality_label.setVisible(False)  # Hide quality selection title
                self.quality_combo.setVisible(False)  # Hide quality selection section
                self.filetype_label.setVisible(False)  # Hide filetype selection title
                self.filetype_combo.setVisible(False)  # Hide filetype selection section
                self.download_button.setVisible(False)  # Hide download button
                self.choose_folder_button.setVisible(False)  # Hide choose folder button
                self.choosen_folder_status.setText("Folder Not Selected")

        except YoutubeDL.utils.DownloadError as e:
            self.status_bar.showMessage(f"Error downloading video info: {e}")
        except Exception as e:
            self.status_bar.showMessage(f"An unexpected error occurred: {e}")


    def hide_l_and_b(self):
        self.download_button.setVisible(False)
        self.choose_folder_button.setVisible(False)
        self.quality_label.setVisible(False)
        self.filetype_label.setVisible(False)
        self.filetype_combo.setVisible(False)
        self.quality_combo.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.choosen_label_quality_text.setText("None")
        self.choosen_label_filetype_text.setText("None")

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

# Worker thread class for downloading
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
        ydl_opts = {
            'format': self.selected_stream['format_id'],
            'outtmpl': os.path.join(self.save_path, f'%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
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

# Main window class
class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        self.setFixedSize(813, 435)

        self.save_path = None
        self.statusBar().showMessage("Ready")
        status_bar = self.statusBar()

        self.url_finder = None

        # Initialize buttons and add debug print statements
        self.find_button = self.findChild(QPushButton, 'search_url_button')
        self.download_button = self.findChild(QPushButton, 'start_download')
        self.choose_folder_button = self.findChild(QPushButton, 'save_path_button')
        self.open_folder_button = self.findChild(QPushButton, 'open_file_path')

        # Debug: Print the types of the loaded UI components
        print(f"Type of find_button: {type(self.find_button)}")
        print(f"Type of download_button: {type(self.download_button)}")
        print(f"Type of choose_folder_button: {type(self.choose_folder_button)}")
        print(f"Type of open_folder_button: {type(self.open_folder_button)}")

        # Ensure the components are properly instantiated
        if not isinstance(self.open_folder_button, QPushButton):
            raise TypeError("open_folder_button is not a QPushButton")

        self.url_input_label = self.findChild(QLabel, 'video_url_label')
        self.url_input = self.findChild(QTextEdit, 'url_input')
        self.quality_label = self.findChild(QLabel, 'select_quality_label')
        self.quality_combo = self.findChild(QComboBox, 'select_quality_combobox')
        self.filetype_label = self.findChild(QLabel, 'save_filetype_label')
        self.filetype_combo = self.findChild(QComboBox, 'save_filetype_combobox')
        self.choosen_folder_status = self.findChild(QLabel, 'selected_path_text')
        self.choosen_label_quality = self.findChild(QLabel, 'selected_quality')
        self.choosen_label_filetype = self.findChild(QLabel, 'selected_filetype')
        self.choosen_label_quality_text = self.findChild(QLabel, 'selected_quality_text')
        self.choosen_label_filetype_text = self.findChild(QLabel, 'selected_filetype_text')
        self.video_name_label = self.findChild(QLabel, 'video_name')
        self.video_name_text = self.findChild(QLabel, 'video_name_text')
        self.progress_bar = self.findChild(QProgressBar, 'progressBar')
        self.progress_label = self.findChild(QLabel, 'download_progress_label')
        self.operation = self.findChild(QLabel, 'operation_text')
        self.status = self.findChild(QLabel, 'status_text')

        self.progress_label.setVisible(True)

        self.video_name_label.setVisible(False)
        self.video_name_text.setVisible(False)

        self.quality_combo.currentTextChanged.connect(self.update_quality_label)
        self.filetype_combo.currentTextChanged.connect(self.update_filetype_label)

        self.download_button.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.quality_label.setVisible(False)
        self.quality_combo.setVisible(False)
        self.filetype_label.setVisible(False)
        self.filetype_combo.setVisible(False)
        self.choose_folder_button.setVisible(False)

        # Ensure proper signal-slot connection
        print("Connecting signals...")
        self.find_button.clicked.connect(self.find_video)
        self.download_button.clicked.connect(self.download)
        self.choose_folder_button.clicked.connect(self.choose_folder)
        self.open_folder_button.clicked.connect(self.open_save_path)
        
        self.show_name_checkbox = self.findChild(QCheckBox, 'check_show_name')
        self.show_name_checkbox.stateChanged.connect(self.update_labels_visibility)

        print("Initialization complete")

    def open_save_path(self):
        if self.save_path and os.path.exists(self.save_path):
            subprocess.Popen(['xdg-open', self.save_path])
        else:
            QMessageBox.warning(self, "Warning", "Invalid or empty save path.")


    def update_labels_visibility(self):
        if self.show_name_checkbox.isChecked():
            self.video_name_label.setVisible(True)
            self.video_name_text.setVisible(True)
        else:
            self.video_name_label.setVisible(False)
            self.video_name_text.setVisible(False)

    def update_quality_label(self, text):
        self.choosen_label_quality_text.setText(text)

    def update_filetype_label(self, text):
        self.choosen_label_filetype_text.setText(text)

    def update_download_progress(self, progress):
        print("Progress received:", progress)  # Debugging
        self.progress_bar.setValue(progress)
        if progress == 100:
            self.download_finished()
            QMessageBox.information(self,"Download Finished", "You Can Open Your Save Path By Clicking ""Open Save PATH")

    def download_finished(self):
        print("Download finished")
        self.statusBar().showMessage("Download finished")
        self.progress_bar.setValue(0)
        self.operation.setText("No Op.")
        self.open_folder_button.setVisible(True)
        self.download_button.setEnabled(True)

    def find_video(self):
        print("Find video button clicked")  # Initial debug print

        self.status.setText("Non-Ready")
        url = self.url_input.toPlainText().strip()
        print(f"URL from input: {url}")

        self.statusBar().showMessage("Finding URL...")
        self.url_finder_thread = URLFinderThread(self.url_input, self.statusBar())
        self.url_finder_thread.found_url.connect(self.handle_url_found)
        self.url_finder_thread.started.connect(self.start_status_check)  
        self.url_finder_thread.finished.connect(self.stop_status_check)
        self.url_finder_thread.finished.connect(self.url_finder_thread.deleteLater)
        self.url_finder_thread.start()
        
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_ydl_status)

    def start_status_check(self):
        self.status_timer.start(100)  # Check every 100 milliseconds

    def stop_status_check(self):
        self.status_timer.stop()
        self.statusBar().showMessage("Ready")

    def check_ydl_status(self):
        # No need to change the message here, as it's set in the run method of URLFinderThread
        if not self.url_finder_thread.isRunning():
            self.status_timer.stop()
            if self.url_finder_thread.info is not None:
                self.handle_url_found(True)
            else:
                self.handle_url_found(False)
    
    def handle_url_found(self, url_found):
        if url_found:
            try:
                url = self.url_input.toPlainText().strip()
                with YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    audio_streams = [stream for stream in info['formats'] if 'acodec' in stream and stream['acodec'] != 'none']
                    video_title = info.get('title', 'Unknown')
                    self.video_name_text.setText(video_title) 

                self.quality_combo.clear()
                audio_streams = sorted(audio_streams, key=lambda x: float(x['abr']) if 'abr' in x and isinstance(x['abr'], str) else float('inf'))
                for stream in reversed(audio_streams):
                    if 'abr' in stream and stream['abr']:  
                        quality_info = f"{stream['abr']} kbps"
                        self.quality_combo.addItem(quality_info, stream)

                filetypes = ['mp3', 'wav', 'flac']  
                self.filetype_combo.clear()
                self.filetype_combo.addItems(filetypes)
                
                self.quality_combo.setVisible(True)
                self.filetype_combo.setVisible(True)
                self.download_button.setVisible(True)
                self.quality_label.setVisible(True)
                self.filetype_label.setVisible(True)
                self.choose_folder_button.setVisible(True)
                self.choosen_folder_status.setText("Folder Not Selected")
                self.operation.setText("None")

            except Exception as e:
                self.statusBar().showMessage(f"Error getting video info: {e}")

        else:
            self.quality_combo.setVisible(False)
            self.filetype_combo.setVisible(False)
            self.download_button.setVisible(False)
            self.quality_label.setVisible(False)
            self.filetype_label.setVisible(False)
            self.choose_folder_button.setVisible(False)
            self.choosen_folder_status.setText("Folder Not Selected")
            self.operation.setText("Finding URL...")

            error = QMessageBox.critical(self, "Error", "Invalid YouTube URL. Please enter a valid URL.")
            if error == QMessageBox.StandardButton.Ok:
                self.statusBar().showMessage("URL Found")

    def download(self):
        self.download_button.setEnabled(False)
        print("called download")
        url = self.url_input.toPlainText().strip()
        if not url:
            self.statusBar().showMessage("Please enter a YouTube URL")
            return

        if not self.save_path:
            QMessageBox.critical(self, "Error", "Please choose a save path.")
            self.download_button.setEnabled(True)
            return

        if self.quality_combo.currentIndex() == -1:
            QMessageBox.critical(self, "Error", "Please select the quality.")
            self.download_button.setEnabled(True)
            return

        if self.save_path and not self.quality_combo.currentIndex() == -1:
            self.status.setText("Ready")

        try:
            with YoutubeDL({'quiet': True}) as ydl:
                print(ydl.extract_info(url, download=False))

            selected_stream = self.quality_combo.currentData()
            print("Selected stream from combo box:", selected_stream)  # Debugging
            print("Type of selected stream from combo box:", type(selected_stream))  # Debugging

            if selected_stream:
                self.operation.setText("Downloading...")

                filetype = self.filetype_combo.currentText()

                self.download_thread = DownloadThread(
                    self.download_button, self.operation, self.status, self.statusBar(), url, selected_stream, filetype, self.save_path
                )
                self.download_thread.download_progress.connect(self.update_download_progress)
                self.download_thread.download_finished.connect(self.download_finished)
                self.download_thread.start()
                print("download started")

            else:
                self.statusBar().showMessage("Error: No stream selected")

        except Exception as e:
            self.statusBar().showMessage("Error: " + str(e))
            print(traceback.format_exc())
    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.save_path = folder
            self.choosen_folder_status.setText(folder)
        else:
            self.save_path = None
            self.choosen_folder_status.setText("Folder Not Selected")
            self.download_button.setVisible(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec())
