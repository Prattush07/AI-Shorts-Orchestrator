import os
import json
from deepgram import DeepgramClient
from deepgram.clients.prerecorded.v1.options import PrerecordedOptions
from deepgram.apps.analyze.v1.types import FileSource
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extract_audio_from_video(video_path: str, output_audio_path: str):
    """
    Extracts audio from video to send to Deepgram.
    We import moviepy inside to avoid circular dependencies if any.
    """
    from moviepy.editor import VideoFileClip
    if os.path.exists(output_audio_path):
        return output_audio_path
        
    print(f"Extracting raw audio from {video_path}...")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(output_audio_path, logger=None, bitrate="128k")
    clip.close()
    return output_audio_path

def transcribe_audio(audio_path: str) -> dict:
    if not DEEPGRAM_API_KEY:
        print("No Deepgram API key found. Returning mock transcript.")
        return {
            "text": "This is a mock transcript because no Deepgram API key was provided.",
            "words": []
        }

    print("Transcribing with Deepgram High-Speed AI...")
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        with open(audio_path, 'rb') as audio_file:
            buffer = audio_file.read()

        payload: FileSource = {
            "buffer": buffer,
            "mimetype": "audio/m4a"
        }
        
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            punctuate=True,
        )
        
        # Call deepgram API
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Parse text from response using dictionary representation
        data = response.to_dict() if hasattr(response, "to_dict") else response
        alt = data["results"]["channels"][0]["alternatives"][0]
        
        transcript_text = alt.get("transcript", "")
        words_array = alt.get("words", [])
        
        print("Deepgram Trancription Complete!")
        return {"text": transcript_text, "words": words_array}
    except Exception as e:
        print(f"Deepgram error: {e}")
        return {"text": "Error transcribing audio.", "words": []}

def find_viral_clips(transcript_data: dict, video_duration: float) -> list:
    transcript = transcript_data.get("text", "")
    words_array = transcript_data.get("words", [])
    
    if not OPENAI_API_KEY or transcript.startswith("This is a mock") or transcript.startswith("Error"):
        print("Mocking viral clips detection due to missing API keys or transcription error.")
        return fallback_viral_clips(video_duration)

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
    You are an AI viral clip finder. Find the best 3 to 7 most engaging, viral-worthy segments from the following transcript.
    Each segment should be 30-50 seconds in ideal length. Since we don't have perfect timestamps from Deepgram in this text, assume the transcript spans the total video duration of {video_duration} seconds and estimate the start_time and end_time (in seconds) linearly based on where the text is located.
    Respond strictly in JSON format as a dictionary with a "clips" array:
    {{
      "clips": [
        {{
           "title": "Catchy TikTok Style Title \U0001F631",
           "start_time": 15.5,
           "end_time": 50.0,
           "description": "Engaging description for this short to drive YouTube/TikTok comments!",
           "hashtags": "#viral #podcast #shorts",
           "score": 95
        }}
      ]
    }}

    Transcript:
    "{transcript[:60000]}"
    """
    
    print("Calling OpenAI to detect Viral Hooks...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        clips = parsed.get("clips", [])
        if not clips:
            return fallback_viral_clips(video_duration)
            
        # Attach the precise word objects for each clip boundary! Shift the timestamps to 0 index!
        for c in clips:
            start_t = float(c.get("start_time", 0.0))
            end_t = float(c.get("end_time", video_duration))
            clip_words = []
            for w in words_array:
                w_start = float(w.get("start", 0))
                w_end = float(w.get("end", 0))
                # Only grab words that exist inside the selected clip boundary!
                if w_start >= start_t and w_start <= end_t:
                    clip_words.append({
                        "word": w.get("punctuated_word", w.get("word", "")),
                        "start_time": w_start - start_t,
                        "end_time": w_end - start_t
                    })
            c["words"] = clip_words
            
        return clips
    except Exception as e:
        print(f"OpenAI error: {e}")
        return fallback_viral_clips(video_duration)


def fallback_viral_clips(video_duration: float) -> list:
    """
    The original math-based slice logic fallback!
    """
    import random
    num_clips = min(7, max(3, int(video_duration / 60)))
    clips = []
    
    for i in range(num_clips):
        clip_dur = random.randint(30, 48)
        interval = max(clip_dur + 5, video_duration / num_clips)
        base_time = i * interval
        max_start = min(base_time + interval - clip_dur, video_duration - clip_dur - 2)
        start_time = base_time if max_start <= base_time else random.uniform(base_time, max_start)
        
        mock_titles = [
            "You Won't Believe What Happened Next! \U0001F631",
            "The BIGGEST Mistake Everyone Makes",
            "I Can't Believe He Said THIS On Camera...",
            "How to Master This Secret Trick \U0001F92F",
            "This Insane Incident Will Blow Your Mind \U0001F525"
        ]
        
        clips.append({
            "start_time": start_time,
            "end_time": min(start_time + clip_dur, video_duration),
            "title": random.choice(mock_titles),
            "description": "This incredible moment changed everything in the video. Watch the full breakdown!\n\nDon't forget to hit Subscribe! \U0001F447",
            "hashtags": "#viral #shorts #mindblown #growth",
            "score": random.randint(85, 99)
        })
    return clips
