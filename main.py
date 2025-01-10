from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import AsyncImage
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.widget import Widget
import yt_dlp
import threading
import os
from pathlib import Path


class VideoDownloaderApp(App):
    def build(self):
        self.title = 'Video Downloader'
        return DownloaderLayout()


class DownloaderLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(20)
        self.spacing = dp(10)

        # URL input field
        self.url_input = TextInput(
            hint_text='Enter Video URL', multiline=False, size_hint_y=None, height=dp(40))
        self.add_widget(self.url_input)

        # Fetch button with reduced width
        button_layout = BoxLayout(size_hint_y=None, height=dp(50))
        self.fetch_button = Button(
            text='Download', size_hint_x=None, width=dp(120))
        self.fetch_button.bind(on_press=self.fetch_video_info)
        button_layout.add_widget(self.fetch_button)
        # This pushes the button to the left
        button_layout.add_widget(Widget())
        self.add_widget(button_layout)

        self.status_label = Label(
            text='No download in progress', size_hint_y=None, height=dp(30))
        self.add_widget(self.status_label)

        self.progress_bar = ProgressBar(
            max=100, size_hint_y=None, height=dp(20))
        self.add_widget(self.progress_bar)

        self.thumbnail_image = AsyncImage(size_hint=(1, None), height=dp(200))
        self.add_widget(self.thumbnail_image)

        self.format_scroll = ScrollView(size_hint=(
            1, None), size=(Window.width, Window.height * 0.4))
        self.format_layout = BoxLayout(
            orientation='vertical', size_hint_y=None)
        self.format_layout.bind(
            minimum_height=self.format_layout.setter('height'))
        self.format_scroll.add_widget(self.format_layout)
        self.add_widget(self.format_scroll)

    def fetch_video_info(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = "Please enter a valid URL"
            return

        self.status_label.text = "Fetching video info..."
        threading.Thread(target=self._fetch_video_info_thread,
                         args=(url,)).start()

    def _fetch_video_info_thread(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = []
            resolutions = set()

            formats.append(('thumbnail', 'Download Thumbnail'))
            formats.append(('audio', 'Best Audio'))
            formats.append(('bestvideo', 'Best Video'))

            if 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec', 'none') != 'none':
                        resolution = f.get('height', 0)
                        if resolution not in resolutions:
                            resolutions.add(resolution)
                            format_id = f['format_id']
                            size = f.get('filesize', None)
                            size_mb = f"{
                                size // (1024 * 1024)} MB" if size else "Unknown size"
                            formats.append(
                                (format_id, f"{resolution}p - {size_mb} (.mp4)"))
            else:
                # If formats are not available, append bestvideo to formats
                formats.append(('bestvideo', 'Best Available Video'))

            thumbnail_url = info.get('thumbnail')
            if thumbnail_url:
                Clock.schedule_once(
                    lambda dt: self.load_thumbnail(thumbnail_url))

            Clock.schedule_once(lambda dt: self.display_formats(url, formats))

        except Exception as e:
            print(f"Error fetching video info: {str(e)}")
            Clock.schedule_once(lambda dt, error_message=str(
                e): self.display_error(f"Error: {error_message}"))

    def load_thumbnail(self, url):
        self.thumbnail_image.source = url

    def display_formats(self, url, formats):
        self.format_layout.clear_widgets()
        for format_id, description in formats:
            btn = Button(text=description, size_hint_y=None, height=dp(50))
            btn.bind(on_press=lambda instance,
                     fmt_id=format_id: self.download_video(url, fmt_id))
            self.format_layout.add_widget(btn)
        self.status_label.text = "Select a format to download"

    def display_error(self, error_message):
        self.status_label.text = error_message

    def download_video(self, url, format_id):
        threading.Thread(target=self._download_thread,
                         args=(url, format_id)).start()

    def _download_thread(self, url, format_id):
        try:
            # Ensure the default download path exists
            default_download_path = str(Path.home() / "Downloads")
            if not os.path.exists(default_download_path):
                os.makedirs(default_download_path)

            # Set up the download options
            ydl_opts = {
                # Template for saving the file
                'outtmpl': f'{default_download_path}/%(title)s.%(ext)s',
                'noplaylist': True,  # Ignore playlists
                'progress_hooks': [self.progress_hook],  # Progress tracking
                'cookiefile': 'assets/cookies.txt',  # Add your cookie file path here
            }

            # Adjust download settings based on selected format
            if format_id == 'thumbnail':
                ydl_opts.update({
                    'skip_download': True,
                    'writethumbnail': True,  # Download thumbnail only
                })
            elif format_id == 'audio':
                ydl_opts['format'] = 'bestaudio'
            elif format_id == 'bestvideo':
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            else:
                ydl_opts['format'] = f'{format_id}+bestaudio/best'

            # Special handling for Snack videos (if needed)
            if 'snackvideo.com' in url:
                ydl_opts.update({
                    'referer': 'https://snackvideo.com/',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                })

            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Notify when the download is complete
            Clock.schedule_once(lambda dt: setattr(
                self.status_label, 'text', "Download completed successfully!"))

        except Exception as e:
            print(f"Error during download: {str(e)}")
            Clock.schedule_once(lambda dt, error_message=str(
                e): self.display_error(f"Error: {error_message}"))
        finally:
            # Reset progress bar after download is finished or failed
            Clock.schedule_once(lambda dt: setattr(
                self.progress_bar, 'value', 0))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes', 0)

            if total_bytes:
                percent = (downloaded_bytes / total_bytes) * 100
                Clock.schedule_once(lambda dt: setattr(
                    self.progress_bar, 'value', percent))
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text',
                                                       f"Downloading: {percent:.2f}% ({downloaded_bytes // (1024 * 1024)} MB of {total_bytes // (1024 * 1024)} MB)"))
            else:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text',
                                                       f"Downloading: {downloaded_bytes // (1024 * 1024)} MB downloaded"))
        elif d['status'] == 'finished':
            Clock.schedule_once(lambda dt: setattr(
                self.status_label, 'text', "Download finished"))


if __name__ == '__main__':
    VideoDownloaderApp().run()
