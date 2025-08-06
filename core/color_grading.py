import cv2
import numpy as np
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

class ColorGrading:
    """Class to apply color grading effects to video clips"""

    def apply_lut(self, clip: VideoFileClip, lut: np.ndarray) -> VideoFileClip:
        """Apply a 3D LUT to the video clip for color grading."""
        def apply_lut_to_frame(frame):
            frame_lut = cv2.transform(frame, lut)
            return np.clip(frame_lut, 0, 255).astype(np.uint8)
        return clip.fl_image(apply_lut_to_frame)

    def adjust_hue(self, clip: VideoFileClip, hue_shift: float) -> VideoFileClip:
        """Adjust the hue of the video clip."""
        def change_hue(frame):
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            hsv[..., 0] = (hsv[..., 0].astype(float) + hue_shift) % 180
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return clip.fl_image(change_hue)

    def adjust_saturation(self, clip: VideoFileClip, saturation_factor: float) -> VideoFileClip:
        """Adjust the saturation of the video clip."""
        def change_saturation(frame):
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            hsv[..., 1] = np.clip(hsv[..., 1] * saturation_factor, 0, 255)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return clip.fl_image(change_saturation)

    def adjust_luminance(self, clip: VideoFileClip, luminance_factor: float) -> VideoFileClip:
        """Adjust the luminance of the video clip."""
        def change_luminance(frame):
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            hsv[..., 2] = np.clip(hsv[..., 2] * luminance_factor, 0, 255)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return clip.fl_image(change_luminance)
