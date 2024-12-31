# VideoStream.py

import cv2

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.cap = cv2.VideoCapture(filename)
        if not self.cap.isOpened():
            raise IOError("Cannot open video file: " + filename)
        self.frameNum = 0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
    def nextFrame(self):
        """Get next frame."""
        ret, frame = self.cap.read()
        if ret:
            self.frameNum += 1
            # Resize frame if needed (optional)
            # frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # Adjust quality if needed
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            if ret:
                return buffer.tobytes()
            else:
                return None
        else:
            return None
        
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
    
    def get_total_frames(self):
        """Return the total number of frames in the video."""
        return self.total_frames
        
    def set_frame(self, frame_number):
        """Set the current frame to the specified frame number."""
        # frame_number is zero-based in OpenCV
        if 0 <= frame_number < self.total_frames:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.frameNum = frame_number
            return True
        return False
        
    def reset(self):
        """Reset to beginning of video."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.frameNum = 0