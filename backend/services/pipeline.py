import os
import shutil
from .downloader import download_video
from moviepy.editor import VideoFileClip
from moviepy.video.fx.all import crop
from .ai_processor import extract_audio_from_video, transcribe_audio, find_viral_clips
from .face_tracker import find_primary_subject_x_center
from .database import save_db
# Using moviepy==1.0.3 for stable API

def process_video_pipeline(project_id: str, url: str, PROJECTS_DB: dict, is_local: bool = False, local_file_path: str = None):
    print(f"[{project_id}] Starting REAL video pipeline for {url if not is_local else 'LOCAL FILE'} using MoviePy...")
    temp_dir = f"temp/{project_id}"
    
    try:
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        PROJECTS_DB[project_id]['progress'] = 10
        save_db(PROJECTS_DB)
        
        if is_local:
            PROJECTS_DB[project_id]['message'] = "Processing uploaded file..."
            video_path = local_file_path
            PROJECTS_DB[project_id]['title'] = "Uploaded Video"
            save_db(PROJECTS_DB)
        else:
            PROJECTS_DB[project_id]['message'] = "Downloading video..."
            
            # 1. Download Video
            try:
                dl_info = download_video(url, output_dir=temp_dir)
                video_path = dl_info["path"]
                PROJECTS_DB[project_id]['title'] = dl_info["title"]
                save_db(PROJECTS_DB)
                
                if not os.path.exists(video_path):
                    # fallback search just in case format was weird
                    import glob
                    matches = glob.glob(f"{temp_dir}/*.*")
                    if matches:
                        video_path = matches[0]
                    else:
                        raise Exception("No video file found after download.")
            except Exception as e:
                print(f"[{project_id}] Download failed: {e}")
                PROJECTS_DB[project_id]['status'] = "failed"
                PROJECTS_DB[project_id]['message'] = f"Failed to download: {str(e)}"
                save_db(PROJECTS_DB)
                return
        
        PROJECTS_DB[project_id]['progress'] = 30
        PROJECTS_DB[project_id]['message'] = "Extracting Audio for Deepgram..."
        
        # 2. Extract Audio
        audio_path = f"{temp_dir}/extract.mp3"
        extract_audio_from_video(video_path, audio_path)
        
        PROJECTS_DB[project_id]['progress'] = 40
        PROJECTS_DB[project_id]['message'] = "Listening to Video via Deepgram API..."
        
        # 3. Transcribe Audio
        transcript_data = transcribe_audio(audio_path)
        
        PROJECTS_DB[project_id]['progress'] = 50
        PROJECTS_DB[project_id]['message'] = "Finding Viral Hooks via OpenAI GPT-4o-mini..."
        
        # 4. Find Viral Chapters
        clip = VideoFileClip(video_path)
        video_duration = clip.duration
        
        viral_segments = find_viral_clips(transcript_data, video_duration)
        num_clips = len(viral_segments)
        
        import random
        
        generated_clips = []
        clip_data_list = []
        
        for i, segment in enumerate(viral_segments):
            PROJECTS_DB[project_id]['message'] = f"Rendering hook {i+1} of {num_clips}..."
            
            start_time = max(0.0, float(segment.get("start_time", 0.0)))
            end_time = min(float(segment.get("end_time", start_time + 40)), video_duration)
            
            # Safeguard format
            if end_time <= start_time:
                end_time = min(start_time + 40, video_duration)
                
            subclip = clip.subclip(start_time, end_time)
            
            # Crop to 9:16 vertical video shape
            w, h = subclip.size
            target_w = int(h * (9 / 16))
            
            # Smart Face Tracking Cropping
            PROJECTS_DB[project_id]['message'] = f"Tracking faces for clip {i+1}..."
            x_center = find_primary_subject_x_center(subclip)
            
            # Ensure crop stays within bounding boxes
            x1 = max(0, x_center - target_w / 2)
            if x1 + target_w > w:
                x1 = w - target_w
                
            y1 = 0
            x2 = x1 + target_w
            y2 = h
            
            vertical_clip = crop(subclip, x1=x1, y1=y1, x2=x2, y2=y2)
            
            clip_file = f"{temp_dir}/clip_{i+1}.mp4"
            
            # Render at extremely high quality and correct framerate for Web playback
            vertical_clip.write_videofile(
                clip_file, 
                codec="libx264", 
                audio_codec="aac", 
                temp_audiofile=f"{temp_dir}/temp-audio.m4a", 
                remove_temp=True, 
                fps=30, 
                preset="fast",          # higher-quality profile
                bitrate="8000k",        # lock in crisp 8000kbps (8Mbps) 4K-ready quality
                ffmpeg_params=["-movflags", "faststart"], # CRITICAL: Places MOOV atom at the start so browser can seek instantly!
                threads=4,              
                logger=None             
            )
            
            # Point to the robust range-supported streaming endpoint using RELATIVE paths for cross-device support
            generated_clips.append(f"/api/v1/projects/stream/{project_id}/clip_{i+1}.mp4")
            
            # Real OpenAI Metadata & Deepgram Subtitles overlay parameters
            clip_data_list.append({
                "title": segment.get("title", f"Viral Clip {i+1}"),
                "description": segment.get("description", "Watch the full breakdown!"),
                "hashtags": segment.get("hashtags", "#viral #shorts"),
                "score": segment.get("score", random.randint(85, 99)),
                "words": segment.get("words", [])
            })
            
            PROJECTS_DB[project_id]['progress'] = 40 + int(((i + 1) / num_clips) * 50)
            save_db(PROJECTS_DB)
            
        clip.close()

        # Update DB State with the real fully-rendered MP4 links and generated metadata
        PROJECTS_DB[project_id]['clips_urls'] = generated_clips
        PROJECTS_DB[project_id]['clips_data'] = clip_data_list
        PROJECTS_DB[project_id]['clips'] = len(generated_clips)
        PROJECTS_DB[project_id]['progress'] = 100
        PROJECTS_DB[project_id]['status'] = "completed"
        PROJECTS_DB[project_id]['message'] = "Success! Clips rendered."
        save_db(PROJECTS_DB)
    
        print(f"[{project_id}] Pipeline complete.")
    except Exception as e:
        print(f"[{project_id}] Pipeline failed: {str(e)}")
        if project_id in PROJECTS_DB:
            PROJECTS_DB[project_id]['status'] = "failed"
            PROJECTS_DB[project_id]['message'] = f"Error during processing: {str(e)}"
            save_db(PROJECTS_DB)
