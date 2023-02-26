import time
from multiprocessing import Process

def writer():
    # Generate a random number (simulate servo commands)
    while (1):
        print("Writer")
        time.sleep(1.0)

def reader():
    # Periodically sample random number and print to console
    while (1):
        print("Reader")
        time.sleep(1.0)

if __name__ == '__main__':
    p1 = Process(target=writer)#, args=('bob',))
    p1.start()
    p2 = Process(target=reader)#, args=('bob',))
    p2.start()
    p1.join()
    p2.join()