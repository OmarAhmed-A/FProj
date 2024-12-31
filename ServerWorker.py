from random import randint
import sys
import traceback
import threading
import socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 'SETUP'      #four rtsp methods
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    SCRUB = 'SCRUB'  # Added for scrubbing

    INIT = 0      #main 3 states 
    READY = 1
    PLAYING = 2
    state = INIT  #indicates current state

    OK_200 = 0    
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}   #store client info in this dictionary

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo   #for initialization of clientinfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()  #for each client we create a thread and in that thread for 
                                                            #that particular client rtsp request are receive

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)   #in the received rtsp request we are receiving data from client
            if data:
                print("Data received:\n" + data.decode("utf-8"))
                self.processRtspRequest(data.decode("utf-8"))  #after that we are calling processrtsp request

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]
        filename = line1[1]
        seq = request[1].split(' ')

        # Handle SCRUB request
        if requestType == self.SCRUB:
            print("processing SCRUB\n")
            if self.state in [self.READY, self.PLAYING]:
                try:
                    # Extract position from request
                    position = None
                    for line in request:
                        if line.startswith('Position'):
                            position = float(line.split(':')[1].strip())
                            break
                    
                    if position is not None:
                        # Calculate target frame
                        total_frames = self.clientInfo['videoStream'].get_total_frames()
                        target_frame = int((position / 100.0) * total_frames)
                        
                        # Pause any current playback
                        if self.state == self.PLAYING:
                            self.clientInfo['event'].set()
                            if 'worker' in self.clientInfo and self.clientInfo['worker'].is_alive():
                                self.clientInfo['worker'].join(timeout=1.0)
                        
                        # Set the video stream to the requested frame
                        if self.clientInfo['videoStream'].set_frame(target_frame):
                            self.replyRtsp(self.OK_200, seq[1])
                            
                            # Prepare for new playback if needed
                            self.clientInfo['event'].clear()
                            
                            # Update state
                            self.state = self.READY
                        else:
                            self.replyRtsp(self.CON_ERR_500, seq[1])
                    else:
                        self.replyRtsp(self.CON_ERR_500, seq[1])
                except Exception as e:
                    print(f"Error during scrubbing: {e}")
                    self.replyRtsp(self.CON_ERR_500, seq[1])
            else:
                self.replyRtsp(self.CON_ERR_500, seq[1])
                
        # Handle other requests (SETUP, PLAY, PAUSE, TEARDOWN)
        elif requestType == self.SETUP:
            if self.state == self.INIT:
                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                    self.clientInfo['session'] = randint(100000, 999999)
                    self.replyRtsp(self.OK_200, seq[1])
                    self.clientInfo['rtpPort'] = request[2].split(' ')[3]
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
                    
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING
                
                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.replyRtsp(self.OK_200, seq[1])
                
                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()
                
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY
                self.clientInfo['event'].set()
                self.replyRtsp(self.OK_200, seq[1])
                
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")
            self.clientInfo['event'].set()
            self.replyRtsp(self.OK_200, seq[1])
            self.clientInfo['rtpSocket'].close()
    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()  #get data using videostream class
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]   #address and port of client
                    port = int(self.clientInfo['rtpPort'])          #so that we can send packet to client using it.
                    self.clientInfo['rtpSocket'].sendto(
                        self.makeRtp(data, frameNumber), (address, port))    #make rtp will create packet and received packet will send to client using address and port
                except:
                    print("Connection Error")
                    # print('-'*60)
                    # traceback.print_exc(file=sys.stdout)
                    # print('-'*60)

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()   #by RtpPacket() class, create rtp packet which consist rtp header and payload(data)

        rtpPacket.encode(version, padding, extension, cc,
                         seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()   #return packet

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""      #reply function which will reply clientinfo if 200 Ok else reply an error message
        if code == self.OK_200:
            #print("200 OK")
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + \
                '\nSession: ' + str(self.clientInfo['session'])
            
            # Add total frames information for SETUP
            if 'videoStream' in self.clientInfo:
                total_frames = self.clientInfo['videoStream'].get_total_frames()
                reply += '\nTotalFrames: ' + str(total_frames)
                
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode('utf-8'))

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
