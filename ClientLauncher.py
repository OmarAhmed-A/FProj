import sys
from tkinter import Tk
from Client import Client

if __name__ == "__main__":
	try:
		serverAddr = sys.argv[1]      #address on which server is running
		serverPort = sys.argv[2]      #rtsp socket port
		rtpPort = sys.argv[3]         #rtp port
		fileName = sys.argv[4]	      #which file we wnat to stream or get from server
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")	
	
	root = Tk()     #create GUI using tkinter library
	
	# Create a new client
	app = Client(root, serverAddr, serverPort, rtpPort, fileName)   #client class
	app.master.title("RTPClient")	
	root.mainloop()
	sys.exit()