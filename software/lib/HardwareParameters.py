"""
Hardware-specific parameters (that don't change often)
"""

# What hardware are you running on?
IS_RASPBERRY_PI = True # Raspberry Pi
# IS_RASPBERRY_PI = False # Desktop

# Camera for kibbie to use:
# CAMERA_DEVICE="software/images/white_background_low_light_both_cats.mp4"    # Playback for dev (white background)
# CAMERA_DEVICE="software/images/20230114-kibbie_feeder.avi"                  # Playback for dev (real floor)
# CAMERA_DEVICE="software/images/20230116-light_day.avi"                      # Playback for dev (real floor, cloudy day with lamp on)
CAMERA_DEVICE=0                                                               # Real camera