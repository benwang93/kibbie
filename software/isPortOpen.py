# Utility to check if a port is open
# Source: https://gist.github.com/betrcode/0248f0fda894013382d7

import socket
def isOpen(ip,port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect((ip, int(port)))
      s.shutdown(2)
      return True
   except:
      return False

print(isOpen("localhost", 8080))