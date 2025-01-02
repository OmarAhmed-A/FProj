# RTSP Video Streaming Application

A Python-based client-server application that implements the RTSP (Real-Time Streaming Protocol) protocol for video streaming. The application supports both MJPEG format videos directly and can automatically convert other video formats to MJPEG for streaming.

## Features

- RTSP protocol implementation
- Real-time video streaming
- Support for MJPEG video format
- Automatic video format conversion
- Client-side playback controls
- Server-side video handling

## Components

- `Client.py` - RTSP client implementation
- `ClientLauncher.py` - Client application entry point
- `Server.py` - RTSP server implementation
- `ServerWorker.py` - Server-side stream handling
- `VideoStream.py` - Video stream management
- `VideoConverter.py` - Video format conversion utility
- `RtpPacket.py` - RTP packet handling

## Prerequisites

- Python 3.x
- FFmpeg (for video conversion)
- Required Python packages:
  - Tkinter (for GUI)
  - PIL (Python Imaging Library)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
```

2. Ensure FFmpeg is installed on your system:

- For Ubuntu/Debian:

  ```bash
  sudo apt-get install ffmpeg
  ```

- For Windows:
  Download and install from [FFmpeg website](https://ffmpeg.org/download.html)

3. Install required Python packages:

```bash
pip install pillow
```

## Usage

1. Start the server:

```bash
python Server.py <server_port>
```

2. Launch the client:

```bash
python ClientLauncher.py
```

3. In the client GUI:
   - Enter the server IP address
   - Enter the server port number
   - Enter the video filename to stream
   - Use the playback controls to manage the stream

## Supported Video Controls

- SETUP: Initialize stream
- PLAY: Start playback
- PAUSE: Pause playback
- TEARDOWN: End stream

## Video Format Support

### Native Support

- MJPEG (.mjpeg, .Mjpeg)

### Convertible Formats

- MP4
- AVI
- MOV
- Other formats supported by FFmpeg

## Project Structure

```sh
│   Client.py           # Client implementation
│   ClientLauncher.py   # Client startup
│   Server.py           # Server implementation
│   ServerWorker.py     # Server stream handler
│   VideoStream.py      # Video stream manager
│   VideoConverter.py   # Format converter
│   RtpPacket.py       # RTP protocol handler
│   README.md          # Documentation
```

## Protocol Implementation

- RTSP (Real-Time Streaming Protocol) for stream control
- RTP (Real-time Transport Protocol) for media delivery
- Custom video frame formatting for efficient transmission

## Error Handling

- Connection error management
- Video format validation
- Stream initialization checks
- Graceful stream termination

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Verify server is running
   - Check port availability
   - Confirm firewall settings

2. **Video Not Playing**
   - Ensure video format is supported
   - Check file permissions
   - Verify FFmpeg installation

3. **Conversion Errors**
   - Confirm FFmpeg installation
   - Check disk space
   - Verify input video integrity
