import cv2
import os
import struct



class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.processed_file = "processed_video.mjpeg"
        self.frameNum = 0
        
        try:
            if not filename.endswith('.Mjpeg'):
                print(f"Converting {filename} to MJPEG format...")
                self.convert_video_to_mjpeg()
                self.file = open(self.processed_file, 'rb')
            else:
                self.file = open(filename, 'rb')
            
            self.frame_positions = [0]
            self.cache_frame_positions()
            
        except Exception as e:
            print(f"Error initializing VideoStream: {e}")
            raise IOError
        
    def convert_video_to_mjpeg(self):
        cap = cv2.VideoCapture(self.filename)
        if not cap.isOpened():
            raise IOError("Cannot open video file")
        
        frame_count = 0
        with open(self.processed_file, 'wb') as outfile:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to JPEG
                _, jpeg_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                frame_bytes = jpeg_frame.tobytes()
                
                # Write size as 5 ASCII digits (original format)
                size_str = f"{len(frame_bytes):05d}".encode('ascii')
                outfile.write(size_str)
                outfile.write(frame_bytes)
                frame_count += 1
                
        cap.release()
            
    def cache_frame_positions(self):
        self.frame_positions = [0]
        self.file.seek(0)
        
        while True:
            try:
                # Read 5-byte ASCII size header
                size_str = self.file.read(5)
                if not size_str or len(size_str) != 5:
                    break
                    
                frame_size = int(size_str.decode('ascii'))
                current_pos = self.file.tell()
                self.frame_positions.append(current_pos + frame_size)
                self.file.seek(frame_size, 1)
                
            except Exception as e:
                break
                
        self.file.seek(0)
        
    def nextFrame(self):
        try:
            size_str = self.file.read(5)
            if not size_str or len(size_str) != 5:
                return None
            
            frame_size = int(size_str.decode('ascii'))
            frame_data = self.file.read(frame_size)
            
            if len(frame_data) == frame_size:
                self.frameNum += 1
                return frame_data
                
        except:
            pass
        return None
        
    def frameNbr(self):
        return self.frameNum
    
    def get_total_frames(self):
        return len(self.frame_positions) - 1
    
    def set_frame(self, frame_number):
        try:
            if 0 <= frame_number < len(self.frame_positions):
                self.file.seek(self.frame_positions[frame_number])
                self.frameNum = frame_number
                return True
            return False
        except:
            return False
            
    def __del__(self):
        try:
            self.file.close()
            if os.path.exists(self.processed_file) and self.filename != self.processed_file:
                os.remove(self.processed_file)
        except:
            pass