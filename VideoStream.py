from VideoConverter import VideoConverter
import os

class VideoStream:
    def __init__(self, filename):
        self.original_filename = filename
        self.frameNum = 0
        self.converted_file = None
        
        try:
            # Check if file needs conversion
            if not filename.lower().endswith(('.mjpeg', '.mjpg')):
                print(f"Input file {filename} is not in MJPEG format. Converting...")
                converter = VideoConverter()
                self.converted_file = f"{os.path.splitext(filename)[0]}_converted.mjpg"
                
                # Perform conversion
                result = converter.convert_video(filename, self.converted_file)
                if result:
                    print("Conversion successful")
                    self.filename = self.converted_file
                else:
                    raise IOError("Video conversion failed")
            else:
                self.filename = filename
            
            self.file = open(self.filename, 'rb')
            self.frame_positions = [0]
            self.cache_frame_positions()
            
        except Exception as e:
            print(f"Error initializing VideoStream: {e}")
            if self.converted_file and os.path.exists(self.converted_file):
                try:
                    os.remove(self.converted_file)
                except:
                    pass
            raise IOError
        
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
            # Clean up converted file if it exists
            if self.converted_file and os.path.exists(self.converted_file):
                os.remove(self.converted_file)
        except:
            pass