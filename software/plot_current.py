import time

import matplotlib.pyplot as plt
import numpy as np

from lib.KibbieSerial import KibbieSerial

class Plotter:
    def __init__(self):
        self.current_history = []
        self.fig, self.ax = plt.subplots()

        self.kbSerial = KibbieSerial()
    

    def sample_and_plot_current(self):
        NUM_SAMPLES_TO_PLOT = 20

        # Add current sample
        for i,channel_sample in enumerate(self.kbSerial.channel_current):
            # Initialize sample if it's the first time receiving it
            if i == len(self.current_history):
                self.current_history.append([channel_sample])
            else:
                self.current_history[i].append(channel_sample)

            # Remove oldest sample if too long
            if len(self.current_history[i]) > NUM_SAMPLES_TO_PLOT:
                self.current_history[i] = self.current_history[i][1:]
            
        # Plot current
        self.fig, self.ax = plt.subplots()
        if len(self.current_history) >= 2:
            # self.ax.plot(range(len(self.current_history[0])), 'g^', self.current_history[0], self.current_history[0]) #, 'g^', x2, y2, 'g-')
            self.ax.plot(range(len(self.current_history[0])), self.current_history[0]) #, 'g^', x2, y2, 'g-')
            self.ax.plot(range(len(self.current_history[1])), self.current_history[1])

        self.ax.set(xlabel='sample number', ylabel='Current (A)',
            title='Kibbie Door Current')
        self.ax.grid()
        self.ax.set_ylim(-0.1, 3.0)

        self.fig.savefig("current.png")
        # self.fig.show()

    def main(self):
        while 1:
            self.kbSerial.update()
            self.sample_and_plot_current()

            time.sleep(0.1)

p = Plotter()
p.main()