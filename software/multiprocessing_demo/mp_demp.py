import random
import time

from multiprocessing import Process, Queue

class MPClass:
    def __init__(self):
        q = Queue()
        self.prefix = "Does everyone see this?"
        p1 = Process(target=self.writer, args=(q,))
        p1.start()
        p2 = Process(target=self.reader, args=(q,))
        p2.start()
        p1.join()
        p2.join()
        print("Done! (should never get here)")

    def writer(self, q):

        self.prefix = "writer was here: " # The writer modifying this does not reflect in the reader

        # Generate a random number (simulate servo commands)
        while (1):
            i = random.randint(0, 100)
            q.put(i)
            print(self.prefix + f"Writer: generated {i}")

            time.sleep(1.0)

    def reader(self, q):
        # Periodically sample random number and print to console
        while (1):
            print(self.prefix + "Reader:")
            while not q.empty():
                i = q.get()
                print(f" - {i}")

            time.sleep(5.0)

if __name__ == '__main__':
    mp = MPClass()