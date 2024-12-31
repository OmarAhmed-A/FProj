import sys
from tkinter import *
import tkinter.messagebox as tkMessageBox
from PIL import Image, ImageTk
import socket
import threading
import traceback
import os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    SETUP_STR = 'SETUP'
    PLAY_STR = 'PLAY'
    PAUSE_STR = 'PAUSE'
    TEARDOWN_STR = 'TEARDOWN'
    SCRUB_STR = 'SCRUB'
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    SCRUB = 4

    RTSP_VER = "RTSP/1.0"
    TRANSPORT = "RTP/UDP"

    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.scrubbing = False
        self.was_playing = False
        self.connectToServer()
        self.frameNbr = 0
        self.scrubValue = 0
        self.totalFrames = 0
        self.expectedFrame = 0
        self.playEvent = None  # Event to control the listener thread
        self.listenerThread = None  # Reference to the listener thread

    def createWidgets(self):
        # Configure style and colors
        BACKGROUND_COLOR = "#2C3E50"
        BUTTON_COLOR = "#34495E"
        TEXT_COLOR = "#ECF0F1"
        ACCENT_COLOR = "#3498DB"
        
        # Configure window
        self.master.configure(bg=BACKGROUND_COLOR)
        self.master.title("Video Streaming Client")
        self.master.geometry("800x600")
        
        # Create main container with grid
        self.main_container = Frame(self.master, bg=BACKGROUND_COLOR)
        self.main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Configure the grid
        self.main_container.rowconfigure(0, weight=1)  # Video display area expands
        self.main_container.rowconfigure(1, weight=0)  # Control buttons do not expand
        self.main_container.rowconfigure(2, weight=0)  # Scrubber does not expand
        self.main_container.columnconfigure(0, weight=1)
        
        # Video display area
        self.label = Label(
            self.main_container,
            bg="#1A1A1A",
            relief=SOLID,
            borderwidth=1
        )
        self.label.grid(row=0, column=0, sticky='nsew', pady=(0, 20))
        
        # Control buttons container
        self.button_frame = Frame(self.main_container, bg=BACKGROUND_COLOR)
        self.button_frame.grid(row=1, column=0, sticky='ew', pady=(0, 15))
        
        # Create buttons with specific sizes
        button_width = 10  # Character width
        button_config = {
            'width': button_width,
            'font': ('Helvetica', 10, 'bold'),
            'borderwidth': 0,
            'pady': 8,
            'cursor': 'hand2',
            'fg': TEXT_COLOR
        }
        
        # Button definitions with their specific colors
        buttons_data = [
            ('SETUP', BUTTON_COLOR, self.setupMovie),
            ('PLAY', "#27AE60", self.playMovie),
            ('PAUSE', "#F39C12", self.pauseMovie),
            ('TEARDOWN', "#C0392B", self.exitClient)
        ]
        
        # Create buttons
        self.buttons = []
        for i, (text, bg_color, command) in enumerate(buttons_data):
            button = Button(
                self.button_frame,
                text=text,
                bg=bg_color,
                command=command,
                **button_config
            )
            button.grid(row=0, column=i, padx=5, sticky='ew')
            self.buttons.append(button)
            button.default_bg = bg_color
        
        # Configure button_frame grid
        for i in range(len(buttons_data)):
            self.button_frame.columnconfigure(i, weight=1)
        self.button_frame.rowconfigure(0, weight=1)
        
        # Add hover effects
        for button in self.buttons:
            button.bind('<Enter>', lambda e, b=button: b.config(bg=ACCENT_COLOR))
            button.bind('<Leave>', lambda e, b=button: b.config(bg=b.default_bg))
        
        # Scrubber container and Scale
        self.scrubber_frame = Frame(self.main_container, bg=BACKGROUND_COLOR)
        self.scrubber_frame.grid(row=2, column=0, sticky='ew')
        
        self.scrubber_frame.columnconfigure(0, weight=1)
        
        self.scrubScale = Scale(
            self.scrubber_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            highlightthickness=0,
            sliderrelief=FLAT,
            activebackground=ACCENT_COLOR,
            troughcolor=BUTTON_COLOR,
            width=10
        )
        self.scrubScale.bind("<Button-1>", self.startScrubbing)
        self.scrubScale.bind("<ButtonRelease-1>", self.handleScrub)
        self.scrubScale.grid(row=0, column=0, sticky='ew')




    def startScrubbing(self, event):
        if self.state not in [self.READY, self.PLAYING]:
            return
        self.scrubbing = True
        if self.state == self.PLAYING:
            self.was_playing = True
            self.pauseMovie()

    def handleScrub(self, event):
        if self.state not in [self.READY, self.PLAYING]:
            return
            
        if not self.scrubbing:  # Ignore if we weren't actually scrubbing
            return
            
        try:
            # Calculate new position
            position = max(0, min(100, self.scrubScale.get()))
            self.scrubValue = int(position)
            self.expectedFrame = max(0, min(self.totalFrames, 
                                        int((self.scrubValue / 100.0) * self.totalFrames)))
            
            # Clear current frame
            self.label.configure(image='')
            self.label.image = None
            
            # Reset connection and send scrub request
            self.resetRtpConnection()
            self.sendRtspRequest(self.SCRUB)
        except Exception as e:
            print("Error during scrubbing:", e)
            self.scrubbing = False
            if self.was_playing:
                self.playMovie()
    def setupMovie(self):
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        if self.state != self.INIT:
            self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()
        os._exit(0)

    def pauseMovie(self):
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        if self.state == self.READY:
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.listenerThread = threading.Thread(target=self.listenRtp)
            self.listenerThread.start()
            self.sendRtspRequest(self.PLAY)

    def handleScrub(self, event):
        """Handles scrub bar interaction"""
        if self.state not in [self.READY, self.PLAYING]:
            return
            
        # Store current state
        self.was_playing = (self.state == self.PLAYING)
        self.scrubbing = True
        
        # Pause if currently playing
        if self.was_playing:
            self.pauseMovie()
        
        try:
            # Calculate new position
            position = max(0, min(100, self.scrubScale.get()))
            self.scrubValue = int(position)
            self.expectedFrame = max(0, min(self.totalFrames, 
                                          int((self.scrubValue / 100.0) * self.totalFrames)))
            
            # Clear current frame
            self.label.configure(image='')
            self.label.image = None
            
            # Reset connection and send scrub request
            self.resetRtpConnection()
            self.sendRtspRequest(self.SCRUB)
        except Exception as e:
            print("Error during scrubbing:", e)
            self.scrubbing = False
            if self.was_playing:
                self.playMovie()

    def resetRtpConnection(self):
        """Resets the RTP connection for scrubbing"""
        try:
            if self.playEvent:
                self.playEvent.set()
                if self.listenerThread and self.listenerThread.is_alive():
                    self.listenerThread.join(timeout=1.0)
            
            if hasattr(self, 'rtpSocket'):
                try:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                self.rtpSocket.close()
            
            self.openRtpPort()
        except Exception as e:
            print("Error resetting RTP connection:", e)

    def updateUI(self):
        """Updates the scrub bar position based on current frame"""
        if self.state == self.PLAYING and self.totalFrames > 0 and not self.scrubbing:
            try:
                current_position = min(100, max(0, (self.frameNbr / self.totalFrames) * 100))
                self.master.after(0, self.scrubScale.set, current_position)
            except Exception as e:
                print("Error updating UI:", e)

    def listenRtp(self):
        while not self.playEvent.is_set():
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()
                    
                    if self.scrubbing:
                        # During scrubbing, accept the frame if it's close to what we expect
                        if abs(currFrameNbr - self.expectedFrame) < 10:
                            self.frameNbr = currFrameNbr
                            imageFile = self.writeFrame(rtpPacket.getPayload())
                            self.master.after(0, self.updateMovie, imageFile)
                            self.scrubbing = False
                    else:
                        # Normal playback
                        if currFrameNbr > self.frameNbr:
                            self.frameNbr = currFrameNbr
                            imageFile = self.writeFrame(rtpPacket.getPayload())
                            self.master.after(0, self.updateUI)
                            self.master.after(0, self.updateMovie, imageFile)
            except Exception as e:
                if self.playEvent.is_set():
                    break
                # print("RTP receive error:", e)
                continue  # Continue listening even if there was a socket timeout

    def writeFrame(self, data):
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        try:
            with open(cachename, "wb") as file:
                file.write(data)
        except Exception as e:
            print("Error writing frame to cache:", e)
        return cachename

    def updateMovie(self, imageFile):
        try:
            # Get the current size of the label
            label_width = self.label.winfo_width()
            label_height = self.label.winfo_height()
            
            # Open the image and resize it to fit the label while maintaining aspect ratio
            image = Image.open(imageFile)
            image_ratio = image.width / image.height
            label_ratio = label_width / label_height
            
            if image_ratio > label_ratio:
                new_width = label_width
                new_height = int(label_width / image_ratio)
            else:
                new_height = label_height
                new_width = int(label_height * image_ratio)
            
            photo = ImageTk.PhotoImage(image.resize((new_width, new_height), Image.LANCZOS))
            
            # Update the label with the new image
            self.label.configure(image=photo)
            self.label.image = photo
        except Exception as e:
            print("Error updating movie frame:", e)

    def connectToServer(self):
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkMessageBox.showwarning('Connection Failed', f'Connection to \'{self.serverAddr}\' failed.')

    def sendRtspRequest(self, requestCode):
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            self.rtspSeq += 1
            request = f"{self.SETUP_STR} {self.fileName} {self.RTSP_VER}"
            request += f"\nCSeq: {self.rtspSeq}"
            request += f"\nTransport: {self.TRANSPORT}; client_port= {self.rtpPort}"
            self.requestSent = self.SETUP

        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1
            request = f"{self.PLAY_STR} {self.fileName} {self.RTSP_VER}"
            request += f"\nCSeq: {self.rtspSeq}"
            request += f"\nSession: {self.sessionId}"
            self.requestSent = self.PLAY

        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = f"{self.PAUSE_STR} {self.fileName} {self.RTSP_VER}"
            request += f"\nCSeq: {self.rtspSeq}"
            request += f"\nSession: {self.sessionId}"
            self.requestSent = self.PAUSE

        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            self.rtspSeq += 1
            request = f"{self.TEARDOWN_STR} {self.fileName} {self.RTSP_VER}"
            request += f"\nCSeq: {self.rtspSeq}"
            request += f"\nSession: {self.sessionId}"
            self.requestSent = self.TEARDOWN

        elif requestCode == self.SCRUB:
            self.rtspSeq += 1
            request = f"{self.SCRUB_STR} {self.fileName} {self.RTSP_VER}"
            request += f"\nCSeq: {self.rtspSeq}"
            request += f"\nSession: {self.sessionId}"
            request += f"\nPosition: {self.scrubValue}"
            self.requestSent = self.SCRUB
        else:
            return

        self.rtspSocket.send(request.encode('utf-8'))
        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        while True:
            try:
                reply = self.rtspSocket.recv(1024)
                if reply:
                    self.parseRtspReply(reply.decode("utf-8"))
                if self.requestSent == self.TEARDOWN:
                    self.rtspSocket.shutdown(socket.SHUT_RDWR)
                    self.rtspSocket.close()
                    break
            except Exception as e:
                print("Error receiving RTSP reply:", e)
                break

    def parseRtspReply(self, data):
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])
        
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            if self.sessionId == 0:
                self.sessionId = session
                
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        self.openRtpPort()
                        for line in lines:
                            if line.startswith('TotalFrames'):
                                self.totalFrames = int(line.split(':')[1])
                                print(f"Total Frames set to: {self.totalFrames}")
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        if self.playEvent:
                            self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardownAcked = 1
                        if self.playEvent:
                            self.playEvent.set()
                            if self.listenerThread:
                                self.listenerThread.join()
                    elif self.requestSent == self.SCRUB:
                        self.frameNbr = self.expectedFrame
                        if self.was_playing:
                            self.playMovie()
                        else:
                            self.state = self.READY
                            self.scrubbing = False

    def openRtpPort(self):
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)
        try:
            self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
        except:
            tkMessageBox.showwarning('Unable to Bind', f'Unable to bind PORT={self.rtpPort}')

    def handler(self):
        self.pauseMovie()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            self.playMovie()