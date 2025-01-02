import subprocess
import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Optional, List, Tuple

class VideoConverter:
    def __init__(self):
        self.ffmpeg_params = {
            'strict': '-2',
            'threads': '0',
            'bitrate': '1000k',
            'scale': '640:360',
            'pixel_format': 'yuvj422p',
            'flags': 'bicubic'
        }
        
    def _create_ffmpeg_command(self, input_file: str, output_file: str) -> List[str]:
        """Creates FFmpeg command with current parameters"""
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        return [
            'ffmpeg',
            '-strict', self.ffmpeg_params['strict'],
            '-hide_banner',
            '-threads', self.ffmpeg_params['threads'],
            '-hwaccel', 'none',
            '-i', input_file,
            '-c:v', 'mjpeg',
            '-b:v', self.ffmpeg_params['bitrate'],
            '-filter_complex', f'[0:v]scale={self.ffmpeg_params["scale"]}[out]',
            '-map', '[out]',
            '-an',
            '-pix_fmt', self.ffmpeg_params['pixel_format'],
            '-sws_flags', self.ffmpeg_params['flags'],
            '-metadata', f'creation_time={current_time}',
            '-y',
            output_file
        ]

    def _convert_to_mjpeg(self, input_file: str, output_file: str) -> bool:
        """Converts input video to MJPEG format"""
        try:
            cmd = self._create_ffmpeg_command(input_file, output_file)
            process = subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg conversion error: {e.stderr.decode()}")
            return False
        except Exception as e:
            print(f"Conversion error: {e}")
            return False

    def _prefix_with_zeroes(self, s: str, n: int) -> str:
        """Adds leading zeros to string"""
        return '0' * (n - len(s)) + s

    def _process_mjpeg(self, input_file: str, output_file: str, 
                      chunk_size: int = 10 * 1024 * 1024) -> Tuple[bool, int]:
        """Processes MJPEG file into final format"""
        try:
            with open(input_file, 'rb') as in_f, open(output_file, 'wb') as out_f:
                buffer = bytearray()
                total_bytes = 0
                frames_processed = 0

                while True:
                    chunk = in_f.read(chunk_size)
                    if not chunk:
                        break

                    buffer.extend(chunk)
                    pos = 0

                    while pos < len(buffer) - 1:
                        if buffer[pos] == 0xFF and buffer[pos + 1] == 0xD8:
                            end_pos = pos + 2
                            while end_pos < len(buffer) - 1:
                                if buffer[end_pos] == 0xFF and buffer[end_pos + 1] == 0xD9:
                                    frame_data = buffer[pos:end_pos + 2]
                                    size_str = self._prefix_with_zeroes(str(len(frame_data)), 5)
                                    out_f.write(size_str.encode())
                                    out_f.write(frame_data)
                                    total_bytes += len(size_str) + len(frame_data)
                                    frames_processed += 1
                                    print(f"\rProcessed frames: {frames_processed}", end='')
                                    pos = end_pos + 2
                                    break
                                end_pos += 1
                            else:
                                break
                        else:
                            pos += 1

                    buffer = buffer[pos:]

                print("\nConversion complete!")
                return True, frames_processed
        except Exception as e:
            print(f"Processing error: {e}")
            return False, 0

    def convert_video(self, input_file: str, output_file: str) -> Optional[str]:
        """
        Converts input video to custom MJPG format
        Returns: Path to output file on success, None on failure
        """
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            return None

        # Create intermediate file
        intermediate_file = f"{input_file}_temp.mjpeg"
        
        try:
            # Convert to MJPEG
            print("Converting to MJPEG format...")
            if not self._convert_to_mjpeg(input_file, intermediate_file):
                return None

            # Process MJPEG to final format
            print("Processing MJPEG to final format...")
            success, frames = self._process_mjpeg(intermediate_file, output_file)
            
            if success:
                print(f"Conversion complete: {frames} frames processed")
                return output_file
            return None

        finally:
            # Cleanup
            if os.path.exists(intermediate_file):
                try:
                    os.remove(intermediate_file)
                except:
                    pass

    def set_parameter(self, param: str, value: str) -> bool:
        """Updates conversion parameters"""
        if param in self.ffmpeg_params:
            self.ffmpeg_params[param] = value
            return True
        return False

    def get_parameter(self, param: str) -> Optional[str]:
        """Retrieves current parameter value"""
        return self.ffmpeg_params.get(param)


if __name__ == "__main__":
    # Command line argument parsing
    parser = argparse.ArgumentParser(description='Video converter')
    parser.add_argument('-c', action='store_true', help='convert only')
    parser.add_argument('-i', required=True, help='input video')
    parser.add_argument('-o', required=True, help='output mjpg video')
    args = parser.parse_args()

    # Print parameters
    print(f"Convert only: {args.c}")
    print(f"Input file: {args.i}")
    print(f"Output file: {args.o}")

    # Initialize converter
    converter = VideoConverter()

    # Perform conversion
    result = converter.convert_video(args.i, args.o)
    
    if result:
        print(f"Successfully converted video to: {result}")
        sys.exit(0)
    else:
        print("Conversion failed")
        sys.exit(1)