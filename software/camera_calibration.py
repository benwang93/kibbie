"""
Script to help calibrate the trapezoidal masks used for each half of the feeder.
"""

import numpy as np
import cv2

import lib.img_tools as img_tools

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
    def __init__(self, camera=None, image_file=None) -> None:
        self.mask = []
        self.camera = camera
        self.image_file = image_file
        self.img = None

        # Mouse coordinates for displaying HSV
        self.mouse_x = 0
        self.mouse_y = 0
    
    # Presents image and overlays any masks
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        curr_frame = self.img.copy()
    
        # Perform white balance
        curr_frame = img_tools.white_balance(curr_frame)

        # Grab HSV at mouse coordinates
        pixel = curr_frame[self.mouse_y][self.mouse_x]
        hsv_pixel = list(cv2.cvtColor(np.array([[pixel]]), cv2.COLOR_BGR2HSV)[0][0])

        curr_frame = cv2.putText(
            img=curr_frame,
            text=f"RGB: {list(pixel)}",
            org=(5, 40),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(0,0,255),
            thickness=1,
            lineType=cv2.LINE_AA
        )
        curr_frame = cv2.putText(
            img=curr_frame,
            text=f"HSV: {hsv_pixel}",
            org=(5, 60),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(0,0,255),
            thickness=1,
            lineType=cv2.LINE_AA
        )

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
        
        # Always update mouse coordinates
        self.mouse_x = x
        self.mouse_y = y

        # Redraw frame
        self.refresh_image()


    def main(self):
        # define a video capture object
        if self.camera:
            vid = cv2.VideoCapture(self.camera)
                
            # Get only the first video frame
            ret, frame = vid.read()
        elif self.image_file:
            frame = cv2.imread(self.image_file)
        else:
            print("No input specified")
            return

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
    # cal = camera_calibration(camera="software/images/white_background_low_light_both_cats.mp4")   # White background video
    # cal = camera_calibration(camera="software/images/20230114-kibbie_feeder.avi")                 # Gray background video on actual kibbie HW
    # cal = camera_calibration(camera="software/images/noodle.png")
    # cal = camera_calibration(camera="software/images/cami.png")
    # cal = camera_calibration(camera='software/images/cami-gray_background.png')
    cal = camera_calibration(camera='software/images/noodle-gray_background.png')

    cal.main()
