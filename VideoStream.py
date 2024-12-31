class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
            # Store frame positions for seeking
            self.frame_positions = [0]  # First frame starts at position 0
            self.cache_frame_positions()
        except:
            raise IOError
        self.frameNum = 0
        
    def cache_frame_positions(self):
        """Cache all frame positions for faster seeking"""
        try:
            current_pos = 0
            self.file.seek(0)
            
            while True:
                data = self.file.read(5)  # Read frame length
                if not data:
                    break
                    
                framelength = int(data)
                current_pos = self.file.tell()  # Get position after length
                self.frame_positions.append(current_pos + framelength)
                self.file.seek(framelength, 1)  # Skip frame data
                
            self.file.seek(0)  # Reset to beginning
        except:
            print("Error caching frame positions")
            self.frame_positions = [0]  # Reset to just the start position
            
    def nextFrame(self):
        """Get next frame."""
        data = self.file.read(5)  # Get the framelength from the first 5 bits
        if data: 
            framelength = int(data)
            # Read the current frame
            data = self.file.read(framelength)
            self.frameNum += 1
            return data
        return None
        
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
    
    def get_total_frames(self):
        """Get total number of frames"""
        return len(self.frame_positions) - 1
    
    def set_frame(self, frame_number):
        """Set the current frame number and position file pointer"""
        try:
            if 0 <= frame_number < len(self.frame_positions):
                self.file.seek(self.frame_positions[frame_number])
                self.frameNum = frame_number
                return True
            return False
        except:
            print("Error seeking to frame")
            return False