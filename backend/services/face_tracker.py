import numpy as np

def find_primary_subject_x_center(subclip):
    """
    Scans a MoviePy video subclip to find the median X-coordinate of the largest face.
    This ensures that when cropping to vertical 9:16, the main speaker stays centered!
    """
    try:
        import cv2
    except ImportError:
        print("OpenCV not installed, falling back to center crop.")
        return subclip.size[0] / 2
        
    try:
        # Load the pre-trained Haar Cascade for Face Detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        w, h = subclip.size
        x_centers = []
        
        duration = subclip.duration
        # Scan 10 frames evenly distributed across the clip to be blazing fast
        times = [i * (duration/15) for i in range(1, 15)]
        
        for t in times:
            try:
                frame = subclip.get_frame(t)
            except Exception:
                continue
                
            # Convert to grayscale for faster processing
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            
            if len(faces) > 0:
                # Find the largest face by area (width * height)
                largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                fx, fy, fw, fh = largest_face
                
                # Calculate the precise center X of this face
                x_center = fx + (fw / 2)
                x_centers.append(x_center)
                
        if x_centers:
            # We use median to completely ignore weird anomalous frames (like someone walking past)
            return np.median(x_centers)
            
        return w / 2 # Default to absolute center if nobody is found
        
    except Exception as e:
        print(f"Face tracking error: {e}")
        return subclip.size[0] / 2
