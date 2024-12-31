import sys, socket

from ServerWorker import ServerWorker

class Server:	
	
	def main(self):
		try:
			SERVER_PORT = int(sys.argv[1])  #port number as a system argument on which server is running
		except:
			print("[Usage: Server.py Server_port]\n")
		rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #create rtsp socket
		rtspSocket.bind(('', SERVER_PORT))  #bind that socket to serverport 
		rtspSocket.listen(5)    #maximum connection for rtspsocket     

		# Receive client info (address,port) through RTSP/TCP session
		while True:
			clientInfo = {}    #start accepting client connection request
			clientInfo['rtspSocket'] = rtspSocket.accept()  #store client info
			ServerWorker(clientInfo).run()  #start running the server		

if __name__ == "__main__":
	(Server()).main()

#python Server.py 1229
#python ClientLauncher.py 127.0.0.1 1229 1219 movie.Mjpeg 