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
        self.masks = [[]]
        self.camera = camera
        self.img = None

    # function to display the coordinates of
    # of the points clicked on the image 
    def click_event(self, event, x, y, flags, params):
        # checking for left mouse clicks
        if event == cv2.EVENT_LBUTTONDOWN:
            self.masks[0].append(x,y)
            self.refresh_image()
    
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        


    def main(self):
        # define a video capture object
        vid = cv2.VideoCapture(self.camera_path)

        # Get only the first video frame
        ret, frame = vid.read()

        # Exit once video finishes
        if not ret:
            return

        # Downsample for faster processing
        self.img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        # setting mouse handler for the image
        # and calling the click_event() function
        cv2.setMouseCallback('img', click_event)
        
        while(True):
            curr_frame = img.copy()

            for mask in self.masks:
                # Draw polygon masks
                # Polygon corner points coordinates
                pts = np.array(mask, np.int32)
                # pts = np.array([[25, 70], [25, 160], 
                #                 [110, 200], [200, 160], 
                #                 [200, 70], [110, 20]],
                #             np.int32)

                pts = pts.reshape((-1, 1, 2))
            
                curr_frame = cv2.polylines(img2=curr_frame, pts=[pts], 
                                    isClosed=True, color=(255, 255, 255), thickness=2)
            
            cv2.imshow("img", img)
            
            # the 'q' button is set as the
            # quitting button you may use any
            # desired button of your choice
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # After the loop release the cap object
        vid.release()
        # Destroy all the windows
        cv2.destroyAllWindows()


########################
# Main
########################
if __name__=="__main__":
    cal = camera_calibration()
    cal.main(camera="software/images/white_background_low_light_both_cats.mp4")
