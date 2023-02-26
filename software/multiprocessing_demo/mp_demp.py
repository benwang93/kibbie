import random
import time

from multiprocessing import Process, Queue

def writer(q):
    # Generate a random number (simulate servo commands)
    while (1):
        i = random.randint(0, 100)
        q.put(i)
        print(f"Writer: generated {i}")

        time.sleep(1.0)

def reader(q):
    # Periodically sample random number and print to console
    while (1):
        print("Reader:")
        while not q.empty():
            i = q.get()
            print(f" - {i}")

        time.sleep(5.0)

if __name__ == '__main__':
    q = Queue()
    p1 = Process(target=writer, args=(q,))
    p1.start()
    p2 = Process(target=reader, args=(q,))
    p2.start()
    p1.join()
    p2.join()