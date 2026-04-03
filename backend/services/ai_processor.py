import os
import json
from deepgram import DeepgramClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extract_audio_from_video(video_path: str, output_audio_path: str):
    """
    Extracts raw audio from video for AI transcription.
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
        return {"text": "No Deepgram API key.", "words": []}

    print("Transcribing with Deepgram High-Speed AI (v3 SDK)...")
    try:
        # Use simple Deepgram client instantiation
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        with open(audio_path, 'rb') as audio_file:
            buffer = audio_file.read()

        payload = {"buffer": buffer}
        options = {
            "model": "nova-2",
            "smart_format": True,
            "punctuate": True,
            "utterances": True,
        }
        
        # We use dictionary-based options to avoid complex import errors
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
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
    
    if not OPENAI_API_KEY or not transcript:
        return fallback_viral_clips(video_duration)

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
    Find 3 to 5 viral-ready segments of 30-50 seconds. Video duration: {video_duration} seconds.
    Respond in STRICT JSON:
    {{
      "clips": [
        {{
           "title": "Title", "start_time": 10.0, "end_time": 45.0, "description": "Desc", "hashtags": "#viral", "score": 95
        }}
      ]
    }}
    Transcript: "{transcript[:5000]}"
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        clips = parsed.get("clips", [])
        
        for c in clips:
            start_t = float(c.get("start_time", 0.0))
            end_t = float(c.get("end_time", video_duration))
            c["words"] = [w for w in words_array if float(w.get("start", 0)) >= start_t and float(w.get("start", 0)) <= end_t]
            
        return clips
    except Exception as e:
        print(f"OpenAI error: {e}")
        return fallback_viral_clips(video_duration)

def fallback_viral_clips(video_duration: float) -> list:
    import random
    num_clips = 3
    clips = []
    for i in range(num_clips):
        start_time = i * (video_duration / 4)
        clips.append({
            "start_time": start_time,
            "end_time": min(start_time + 40, video_duration),
            "title": f"Viral Moment #{i+1}",
            "description": "Auto-clipped highlights.",
            "hashtags": "#viral #shorts",
            "score": random.randint(85, 99)
        })
    return clips
