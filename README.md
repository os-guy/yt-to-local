Welcome to the YouTube MP3 Downloader Project.
This project allows you to download YouTube videos in MP3 format.
This project was made on Python Programming Language.

## Requirements

__YOU SHOULD INSTALL PYTHON TO RUN IT.__
__AND PIP, FOR INSTALLING DEPENDENCIES.__
Most of the Linux distros are already installing it.

- pyqt6
- pytube
- moviepy
- yt-dlp
- ffprobe
- ffmpeg
- youtube_dl

## Building

### On Linux

- First of all, you should clone this repo with the following command:
`git clone https://github.com/os-guy/yt-to-local.git`

- After that, open the directory with following:
`cd yt-to-local`

- Install the __requirements__ with the following command:
`pip install -r requirements.txt`

### On Windows

- Download the `.zip` file and extract it.

- Copy the `requirements.txt` path.

- Open cmd and type: `pip install -r <Reqs-Path-Here>`

#### Adding FFmpeg To PATH

1. Type system *variables* into the search bar and click the __Edit the system environment variables__ option.
2. Under the *User variables* section, select *Path* and click the __Edit__ button.
3. Choose __New__ from the side menu.
4. Add `C:\ffmpeg\bin` to the empty field and confirm changes with __OK__.
   
*The change in the Path variable line confirms the FFmpeg is added to PATH.*
*This should add __FFprobe__ to PATH too. Because __FFmpeg__ and __FFprobe__ are typically in the same folder.*

## Running The Project

__THIS PROJECT IS IN ALPHA__.
You can run this with following:

#### On Linux
- Open terminal and type `python3 [PROJECT-PATH].py`
#### On Windows
- Double click on `yt-to-local-windows.py`. It should run automatically.

## Project State

This project is new and the developer is still working on it.
So, if you'll be able to find some issues, please report to us.
Problems can be solve.
