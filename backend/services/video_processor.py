import ffmpeg
import os

def extract_audio(video_path: str, output_audio_path: str = None) -> str:
    """
    Extracts the audio track from a video file as a WAV file for AI transcription.
    """
    if not output_audio_path:
        base, _ = os.path.splitext(video_path)
        output_audio_path = f"{base}.wav"

    try:
        (
            ffmpeg
            .input(video_path)
            .output(output_audio_path, acodec='pcm_s16le', ac=1, ar='16k')
            .overwrite_output()
            .run(quiet=False)
        )
        return output_audio_path
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        raise e

def crop_and_cut_video(video_path: str, start_time: float, end_time: float, output_path: str):
    """
    Cuts a segment of the video and crops it to 9:16 vertical ratio.
    """
    try:
        (
             ffmpeg
             .input(video_path, ss=start_time, to=end_time)
             .filter('scale', -1, 1920)         # scale to vertical height
             .filter('crop', 1080, 1920)        # crop to vertical width
             .output(output_path, c_v='libx264', c_a='aac')
             .overwrite_output()
             .run(quiet=False) # remove quiet=False in production
        )
        return output_path
    except ffmpeg.Error as e:
         print(f"FFmpeg error: {e.stderr.decode()}")
         raise e
