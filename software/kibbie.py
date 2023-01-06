import numpy as np
import cv2
import time

import lib.color_quantization as cq
import lib.img_tools as img_tools

########################
# Constants
########################

# Scale factor applied to the image dimensions to speed up processing
# and get the image to fit on the screen
#
# The results from this script will be scaled back up by this same scale
# so that kibbie.py can scale it back down according to its own scale.
# scale = 0.5 # For quality
scale = 0.25
# scale = 0.1 # For speed


########################
# Main class
########################
class kibbie:
    # camera: string filepath or int representing video capture device index
    # config: config information, including (per cat):
    #   - Mask polygon (list of [x, y] points describing polygon on UNSCALED image)
    #   - Dispenses per day (float)
    def __init__(self, camera, config) -> None:
        self.camera = camera

        # Preprocess the configuration
        for i in range(len(config["cats"])):
            config["cats"][i]["mask"] = [[x[0] * scale, x[1] * scale] for x in config["cats"][i]["mask"]]
        self.config = config

        # Placeholder for current scaled frame from camera
        self.img = None

        # Placeholder for current scaled and quantized frame
        self.quantized = None

        # Timestamp of last frame - used to calculate FPS to display on debug image
        self.last_time_s = None
    

    # Presents image and overlays any masks
    def refresh_image(self):
        if self.img is None:
            return
        
        # Draw image
        curr_frame = self.quantized.copy()

        for config in self.config["cats"]:
            # Draw polygon masks
            # Polygon corner points coordinates
            pts = np.array(config["mask"], np.int32)
            pts = pts.reshape((-1, 1, 2))
        
            curr_frame = cv2.polylines(img=curr_frame, pts=[pts], 
                                isClosed=True, color=(255, 255, 255), thickness=2)
        
        # Calculate FPS
        curr_time_s = time.time()
        fps = 1 / (curr_time_s - self.last_time_s)
        self.last_time_s = curr_time_s
        curr_frame = cv2.putText(img=curr_frame, text=f"FPS: {fps:.2f}", org=(5, 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)

        cv2.imshow("img", self.img)
        cv2.imshow("quantized", curr_frame)

        height_px = curr_frame.shape[0]
        cv2.moveWindow("img",       0, 1 * (height_px + 50))
        cv2.moveWindow("quantized", 0, 2 * (height_px + 50))


    def main(self):
        # define a video capture object
        vid = cv2.VideoCapture(self.camera)
        
        # Track FPS
        self.last_time_s = time.time()
        
        while(True):
            # Capture the video frame by frame
            ret, frame = vid.read()

            # Exit once video finishes
            if not ret:
                break

            # Downsample for faster processing
            self.img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

            # Perform white balance
            if self.config["enableWhiteBalance"]:
                self.img = img_tools.white_balance(self.img)

            # Quantize image colors
            self.quantized = cq.quantizeColors(self.img)

            # Display debug image
            self.refresh_image()

            # Compute dominant colors
            unique,freq = cq.getDominantColors(self.quantized)
            cq.plotDominantColors(self.img, unique, freq)
            
            # Hit 'q' key to quit
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
    kb = kibbie(camera="software/images/white_background_low_light_both_cats.mp4", config={
        "enableWhiteBalance": True,
        "cats":[
            {
                "name": "Noodle",
                # Use the "unscaled" coordinates from `camera_calibration.py`
                "mask": [
                    [676.0, 480.0], [680.0, 88.0], [752.0, 14.0], [1006.0, 16.0], [1102.0, 128.0], [1108.0, 372.0], [950.0, 408.0], [946.0, 482.0]
                ],
                "colorProfile": "TBD...",
                "dispensesPerDay": 3,
            },
        ],
    })
    kb.main()
