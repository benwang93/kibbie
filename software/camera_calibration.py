"""
Script to help calibrate the trapezoidal masks used for each half of the feeder.
"""

import numpy as np
import cv2

########################
# Constants
########################

# Scale factor applied to the image dimensions to speed up processing
# and get the image to fit on the screen
#
# The results from this script will be scaled back up by this same scale
# so that kibbie.py can scale it back down according to its own scale.
scale = 0.5


########################
# Main class
########################
class camera_calibration:
    # camera: string filepath or int representing video capture device index
    def __init__(self, camera) -> None:
        self.mask = []
        self.camera = camera
        self.img = None
    
    # Presents image and overlays any masks
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        curr_frame = self.img.copy()

        if len(self.mask) > 0:
            # Draw polygon masks
            # Polygon corner points coordinates
            pts = np.array(self.mask, np.int32)
            pts = pts.reshape((-1, 1, 2))
        
            curr_frame = cv2.polylines(img=curr_frame, pts=[pts], 
                                isClosed=True, color=(255, 255, 255), thickness=2)
        
        cv2.imshow("img", curr_frame)
        

    # function to display the coordinates of
    # of the points clicked on the image 
    def click_event(self, event, x, y, flags, params):
        # checking for left mouse clicks
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mask.append([x,y])
            print(f"Registered click at ({x}, {y}). masks is now: {self.mask}")
            self.refresh_image()


    def main(self):
        # define a video capture object
        vid = cv2.VideoCapture(self.camera)

        # Get only the first video frame
        ret, frame = vid.read()

        # Exit once video finishes
        if not ret:
            return

        # Downsample for faster processing
        self.img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        
        # Draw initial image
        self.refresh_image()

        # setting mouse handler for the image
        # and calling the click_event() function
        cv2.setMouseCallback('img', self.click_event)

        # Quit on key press
        cv2.waitKey(0)
        
        # After the loop release the cap object
        vid.release()
        # Destroy all the windows
        cv2.destroyAllWindows()

        # Print final polygon
        print("\n***************************")
        print(f"Final mask polygon (scaled at {scale}): {self.mask}")
        print(f"Final mask polygon unscaled: {[[x[0] / scale, x[1] / scale] for x in self.mask]}")
        height_px = self.img.shape[0]
        width_px = self.img.shape[1]
        print(f"Final mask polygon normalized 0 to 1: {[[x[0] / scale / width_px, x[1] / scale / height_px] for x in self.mask]}")
        print("***************************")


########################
# Main
########################
if __name__=="__main__":
    cal = camera_calibration(camera="software/images/white_background_low_light_both_cats.mp4")
    cal.main()
