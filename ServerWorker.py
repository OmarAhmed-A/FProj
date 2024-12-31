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

    def processRtspRequest(self, data):     #we are processing the rtsp request sent by the client
        """Process RTSP request sent from the client."""  #we will process the request that which type of request is this?
                                                          #and do further process according to that
        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY             #update state to ready state if it is in init state
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])   

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)

                # Send RTSP reply
                self.replyRtsp(self.OK_200, seq[1])   #server will reply to that setup request

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = request[2].split(' ')[3]

        # Process PLAY request
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING      #change state to playing

                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)       #create socket for rtp/udp to sent data from server to client which will use udp protocol

                self.replyRtsp(self.OK_200, seq[1])    #respond to playing request that i have received a request

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()  #create a thread for particular client to send data using rtp protocol
                self.clientInfo['worker'] = threading.Thread(
                    target=self.sendRtp)
                self.clientInfo['worker'].start()   #start thread

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY    #change state

                self.clientInfo['event'].set()  #stop running thread

                self.replyRtsp(self.OK_200, seq[1])  #respond that i have process pause request 

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            self.clientInfo['event'].set()   #stop the thread

            self.replyRtsp(self.OK_200, seq[1])  #respond that i have process teardown request

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()   #close the rtp socket
        elif requestType == self.SCRUB:
            print("processing SCRUB\n")
            
            # Get the requested position from the request
            for line in request:
                if line.startswith('Position'):
                    try:
                        position = float(line.split(':')[1].strip())
                        total_frames = self.clientInfo['videoStream'].get_total_frames()
                        target_frame = int((position / 100.0) * total_frames)
                        
                        # Pause any current playback
                        self.clientInfo['event'].set()
                        
                        # Set the video stream to the requested frame
                        if self.clientInfo['videoStream'].set_frame(target_frame):
                            self.replyRtsp(self.OK_200, seq[1])
                            # Reset the event flag to allow playback to continue
                            self.clientInfo['event'].clear()
                        else:
                            self.replyRtsp(self.CON_ERR_500, seq[1])
                        break
                    except:
                        self.replyRtsp(self.CON_ERR_500, seq[1])

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
