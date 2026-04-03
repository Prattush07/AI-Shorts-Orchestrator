import yt_dlp
import os
import imageio_ffmpeg

def download_video(url: str, output_dir: str = "temp") -> dict:
    """
    Downloads a video from a URL using yt-dlp.
    Returns a dict containing 'path' and 'title'.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Use the exact executable path so yt-dlp can merge 4k/1080p streams successfully
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # yt-dlp configuration to download maximum 1080p to avoid massive file sizes
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': f'{output_dir}/video.mp4',
        'ffmpeg_location': ffmpeg_exe,
        'noplaylist': True,
        'quiet': False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return {"path": filename, "title": info.get("title", "Unknown Title")}
    except Exception as e:
        print(f"Error downloading video: {e}")
        raise e
