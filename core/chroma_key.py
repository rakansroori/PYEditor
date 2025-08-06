"""
Chroma Key (Green Screen) module for PyVideoEditor
Handles background replacement and chroma key effects
"""

import cv2
import numpy as np
from typing import Tuple, Optional
try:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip

class ChromaKeyProcessor:
    """Class for chroma key (green screen) processing"""
    
    def __init__(self):
        self.key_color = (0, 255, 0)  # Default green screen color (RGB)
        self.tolerance = 40           # Color tolerance for keying
        self.edge_softness = 5        # Edge softening radius
        self.spill_suppression = 0.5  # Spill suppression strength
        
    def set_key_color(self, color: Tuple[int, int, int]):
        """Set the chroma key color (RGB)"""
        self.key_color = color
        
    def set_tolerance(self, tolerance: int):
        """Set the color tolerance (0-255)"""
        self.tolerance = max(0, min(255, tolerance))
        
    def set_edge_softness(self, softness: int):
        """Set edge softness (0-20)"""
        self.edge_softness = max(0, min(20, softness))
        
    def set_spill_suppression(self, strength: float):
        """Set spill suppression strength (0.0-1.0)"""
        self.spill_suppression = max(0.0, min(1.0, strength))
    
    def create_mask(self, frame: np.ndarray) -> np.ndarray:
        """Create alpha mask for chroma key"""
        # Convert BGR to HSV for better color keying
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        
        # Convert key color to HSV
        key_color_bgr = np.uint8([[list(reversed(self.key_color))]])  # RGB to BGR
        key_color_hsv = cv2.cvtColor(key_color_bgr, cv2.COLOR_BGR2HSV)[0][0]
        
        # Define range for key color in HSV
        hue_range = 10  # Hue tolerance
        sat_range = 255  # Full saturation range
        val_range = 255  # Full value range
        
        # Calculate HSV ranges
        lower_bound = np.array([
            max(0, key_color_hsv[0] - hue_range),
            max(0, key_color_hsv[1] - sat_range),
            max(0, key_color_hsv[2] - val_range)
        ])
        
        upper_bound = np.array([
            min(179, key_color_hsv[0] + hue_range),
            255,
            255
        ])
        
        # Create initial mask
        mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Apply Gaussian blur for edge softening
        if self.edge_softness > 0:
            mask = cv2.GaussianBlur(mask, (self.edge_softness * 2 + 1, self.edge_softness * 2 + 1), 0)
        
        # Invert mask (0 = key color, 255 = keep)
        mask = 255 - mask
        
        return mask.astype(np.float32) / 255.0
    
    def apply_spill_suppression(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Apply spill suppression to reduce color bleeding"""
        if self.spill_suppression <= 0:
            return frame
            
        # Convert to HSV for spill suppression
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        
        # Target the key color hue
        key_color_bgr = np.uint8([[list(reversed(self.key_color))]])
        key_hue = cv2.cvtColor(key_color_bgr, cv2.COLOR_BGR2HSV)[0][0][0]
        
        # Create spill mask (areas with similar hue to key color)
        hue_diff = np.abs(hsv_frame[:, :, 0] - key_hue)
        hue_diff = np.minimum(hue_diff, 180 - hue_diff)  # Handle hue wraparound
        spill_mask = (hue_diff < 30) & (mask < 0.9)  # Areas with key color spill
        
        # Reduce saturation in spill areas
        hsv_frame[:, :, 1][spill_mask] *= (1.0 - self.spill_suppression)
        
        # Convert back to RGB
        hsv_frame = np.clip(hsv_frame, 0, 255).astype(np.uint8)
        return cv2.cvtColor(hsv_frame, cv2.COLOR_HSV2RGB)
    
    def composite_with_background(self, foreground: np.ndarray, background: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Composite foreground with background using alpha mask"""
        # Ensure background matches foreground dimensions
        if background.shape[:2] != foreground.shape[:2]:
            background = cv2.resize(background, (foreground.shape[1], foreground.shape[0]))
        
        # Expand mask to 3 channels
        if len(mask.shape) == 2:
            mask = np.stack([mask] * 3, axis=2)
        
        # Composite: result = foreground * mask + background * (1 - mask)
        result = (foreground * mask + background * (1.0 - mask)).astype(np.uint8)
        return result
    
    def process_frame(self, foreground_frame: np.ndarray, background_frame: np.ndarray = None) -> np.ndarray:
        """Process a single frame with chroma key"""
        # Create alpha mask
        mask = self.create_mask(foreground_frame)
        
        # Apply spill suppression
        processed_foreground = self.apply_spill_suppression(foreground_frame, mask)
        
        if background_frame is not None:
            # Composite with background
            result = self.composite_with_background(processed_foreground, background_frame, mask)
        else:
            # Return with transparent background (add alpha channel)
            if len(mask.shape) == 2:
                alpha_channel = (mask * 255).astype(np.uint8)
            else:
                alpha_channel = (mask[:, :, 0] * 255).astype(np.uint8)
            result = np.dstack([processed_foreground, alpha_channel])
        
        return result
    
    def apply_to_clip(self, clip: VideoFileClip, background_clip: VideoFileClip = None) -> VideoFileClip:
        """Apply chroma key to entire video clip"""
        if background_clip is None:
            # Create transparent background
            def process_frame_transparent(get_frame, t):
                frame = get_frame(t)
                return self.process_frame(frame)
            
            processed_clip = clip.fl(process_frame_transparent)
            
        else:
            # Composite with background clip
            def process_frame_composite(get_frame, t):
                foreground_frame = clip.get_frame(t)
                background_frame = background_clip.get_frame(min(t, background_clip.duration - 0.01))
                return self.process_frame(foreground_frame, background_frame)
            
            # Create new clip with composited frames
            processed_clip = clip.fl(process_frame_composite, apply_to=['mask'])
        
        return processed_clip

class ChromaKeyManager:
    """Manager for chroma key operations"""
    
    def __init__(self):
        self.processor = ChromaKeyProcessor()
        self.background_image = None
        self.background_clip = None
        
    def set_background_image(self, image_path: str):
        """Set background image"""
        try:
            self.background_image = cv2.imread(image_path)
            if self.background_image is not None:
                self.background_image = cv2.cvtColor(self.background_image, cv2.COLOR_BGR2RGB)
                return True
        except Exception as e:
            print(f"Error loading background image: {e}")
        return False
    
    def set_background_clip(self, clip: VideoFileClip):
        """Set background video clip"""
        self.background_clip = clip
    
    def apply_chroma_key(self, clip: VideoFileClip, 
                        key_color: Tuple[int, int, int] = (0, 255, 0),
                        tolerance: int = 40,
                        edge_softness: int = 5,
                        spill_suppression: float = 0.5) -> VideoFileClip:
        """Apply chroma key with specified parameters"""
        
        # Configure processor
        self.processor.set_key_color(key_color)
        self.processor.set_tolerance(tolerance)
        self.processor.set_edge_softness(edge_softness)
        self.processor.set_spill_suppression(spill_suppression)
        
        # Choose background
        background = None
        if self.background_clip is not None:
            background = self.background_clip
        elif self.background_image is not None:
            # Convert image to clip
            background = ImageClip(self.background_image, duration=clip.duration)
        
        return self.processor.apply_to_clip(clip, background)
    
    def preview_mask(self, clip: VideoFileClip, time: float = 0.0) -> np.ndarray:
        """Preview the chroma key mask at a specific time"""
        frame = clip.get_frame(time)
        mask = self.processor.create_mask(frame)
        
        # Convert mask to viewable format (0-255)
        return (mask[:, :, 0] * 255).astype(np.uint8)
    
    def get_available_presets(self) -> dict:
        """Get available chroma key presets"""
        return {
            'green_screen': {
                'key_color': (0, 255, 0),
                'tolerance': 40,
                'edge_softness': 5,
                'spill_suppression': 0.5
            },
            'blue_screen': {
                'key_color': (0, 0, 255),
                'tolerance': 40,
                'edge_softness': 5,
                'spill_suppression': 0.5
            },
            'red_screen': {
                'key_color': (255, 0, 0),
                'tolerance': 40,
                'edge_softness': 5,
                'spill_suppression': 0.5
            },
            'high_quality': {
                'key_color': (0, 255, 0),
                'tolerance': 30,
                'edge_softness': 8,
                'spill_suppression': 0.7
            },
            'fast_processing': {
                'key_color': (0, 255, 0),
                'tolerance': 50,
                'edge_softness': 2,
                'spill_suppression': 0.3
            }
        }
    
    def apply_preset(self, preset_name: str):
        """Apply a chroma key preset"""
        presets = self.get_available_presets()
        if preset_name in presets:
            preset = presets[preset_name]
            self.processor.set_key_color(preset['key_color'])
            self.processor.set_tolerance(preset['tolerance'])
            self.processor.set_edge_softness(preset['edge_softness'])
            self.processor.set_spill_suppression(preset['spill_suppression'])
            return True
        return False
