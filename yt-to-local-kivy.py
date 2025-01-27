import sys
import os
import subprocess
import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.modalview import ModalView
from threading import Thread
from yt_dlp import YoutubeDL

class URLFinder(Thread):
    def __init__(self, url_input, status_label, quality_spinner, filetype_spinner, download_button, choose_folder_button, status_bar):
        super().__init__()
        self.url_input = url_input
        self.status_label = status_label
        self.quality_spinner = quality_spinner
        self.filetype_spinner = filetype_spinner
        self.download_button = download_button
        self.choose_folder_button = choose_folder_button
        self.status_bar = status_bar

    def run(self):
        url = self.url_input.text.strip()
        if not url.startswith(("http://", "https://")):
            self.status_bar.text = "Invalid URL: Must start with http:// or https://"
            return
        if "youtube.com" not in url and "youtu.be" not in url:
            self.status_bar.text = "Invalid URL: Not a YouTube URL"
            return

        try:
            self.status_label.text = "Finding URL..."
            ydl_opts = {'quiet': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_streams = [stream for stream in info['formats'] if 'acodec' in stream and stream['acodec'] != 'none']

            if audio_streams:
                self.status_bar.text = "URL found"
                self.quality_spinner.values = [f"{stream['abr']} kbps" for stream in sorted(audio_streams, key=lambda x: float(x['abr']) if 'abr' in x and isinstance(x['abr'], str) else float('inf'))]
                self.filetype_spinner.values = ['mp3', 'wav', 'flac']
                self.download_button.disabled = False
                self.choose_folder_button.disabled = False
            else:
                self.status_bar.text = "No audio streams found"

        except Exception as e:
            self.status_bar.text = f"An unexpected error occurred: {e}"

class DownloadThread(Thread):
    def __init__(self, url, selected_stream, filetype, save_path, progress_bar, status_label, status_bar):
        super().__init__()
        self.url = url
        self.selected_stream = selected_stream
        self.filetype = filetype
        self.save_path = save_path
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.status_bar = status_bar

    def run(self):
        ydl_opts = {
            'format': self.selected_stream,
            'outtmpl': os.path.join(self.save_path, f'%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
        }

        self.status_label.text = "Downloading..."
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.status_bar.text = "Download finished"
        except Exception as e:
            self.status_bar.text = f"An error occurred: {e}"

    def progress_hook(self, progress):
        if progress['status'] == 'downloading':
            total_bytes = progress.get('total_bytes')
            downloaded_bytes = progress.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                percent = int(downloaded_bytes / total_bytes * 100)
                Clock.schedule_once(lambda dt: self.progress_bar.set_value(percent))

class YouTubeDownloaderApp(App):
    def build(self):
        self.save_path = None

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.url_input = TextInput(hint_text='Enter YouTube URL', multiline=False)
        layout.add_widget(self.url_input)

        self.status_bar = Label(text='Ready')
        layout.add_widget(self.status_bar)

        self.find_button = Button(text='Find URL')
        self.find_button.bind(on_press=self.find_video)
        layout.add_widget(self.find_button)

        self.quality_spinner = Spinner(text='Select Quality', values=[])
        layout.add_widget(self.quality_spinner)

        self.filetype_spinner = Spinner(text='Select Filetype', values=[])
        layout.add_widget(self.filetype_spinner)

        self.download_button = Button(text='Download', disabled=True)
        self.download_button.bind(on_press=self.download)
        layout.add_widget(self.download_button)

        self.choose_folder_button = Button(text='Choose Save Path', disabled=True)
        self.choose_folder_button.bind(on_press=self.choose_folder)
        layout.add_widget(self.choose_folder_button)

        self.progress_bar = ProgressBar(max=100)
        layout.add_widget(self.progress_bar)

        return layout

    def find_video(self, instance):
        self.status_bar.text = "Finding URL..."
        url_finder = URLFinder(self.url_input, self.status_bar, self.quality_spinner, self.filetype_spinner, self.download_button, self.choose_folder_button, self.status_bar)
        url_finder.start()

    def download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.status_bar.text = "Please enter a YouTube URL"
            return

        if not self.save_path:
            self.status_bar.text = "Please choose a save path"
            return

        selected_stream = self.quality_spinner.text
        filetype = self.filetype_spinner.text

        download_thread = DownloadThread(url, selected_stream, filetype, self.save_path, self.progress_bar, self.status_bar, self.status_bar)
        download_thread.start()

    def choose_folder(self, instance):
        content = FileChooserIconView()
        popup = Popup(title="Select Directory", content=content, size_hint=(0.9, 0.9))
        content.bind(on_submit=lambda instance, selection, touch: self.set_save_path(selection, popup))
        popup.open()

    def set_save_path(self, selection, popup):
        if selection:
            self.save_path = selection[0]
            self.status_bar.text = f"Save path: {self.save_path}"
        popup.dismiss()

if __name__ == "__main__":
    YouTubeDownloaderApp().run()
