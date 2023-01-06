import numpy as np
import cv2
import time

import lib.color_quantization as cq


def main():
    # define a video capture object
    # vid = cv2.VideoCapture(0)
    filepath = "software/images/white_background_low_light_both_cats.mp4"
    vid = cv2.VideoCapture(filepath)
    
    # Track FPS
    last_time_s = time.time()
    
    while(True):
        # Capture the video frame
        # by frame
        ret, frame = vid.read()

        # Exit once video finishes
        if not ret:
            break

        # Downsample for faster processing
        scale = 0.5 #0.1
        img = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        quantized = cq.quantizeColors(img)

        # Draw polygon masks
        # Polygon corner points coordinates
        pts = np.array([[25, 70], [25, 160], 
                        [110, 200], [200, 160], 
                        [200, 70], [110, 20]],
                    np.int32)

        pts = pts.reshape((-1, 1, 2))
        
        quantized = cv2.polylines(img=quantized, pts=[pts], 
                            isClosed=True, color=(255, 255, 255), thickness=2)
        
        # Calculate FPS
        curr_time_s = time.time()
        fps = 1 / (curr_time_s - last_time_s)
        last_time_s = curr_time_s
        quantized = cv2.putText(img=quantized, text=f"FPS: {fps:.2f}", org=(5, 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255,255,255), thickness=1, lineType=cv2.LINE_AA)

        # cv2.imwrite('output.jpg', quantized)
        cv2.imshow("img", img)
        cv2.imshow("quantized", quantized)

        unique,freq = cq.getDominantColors(quantized)
        cq.plotDominantColors(img, unique, freq)
        
        # the 'q' button is set as the
        # quitting button you may use any
        # desired button of your choice
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # After the loop release the cap object
    vid.release()
    # Destroy all the windows
    cv2.destroyAllWindows()

if __name__=="__main__":
    main()
