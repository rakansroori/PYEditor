"""
Video effects plugin system
Extensible effects that can be applied to video clips
"""

from abc import ABC, abstractmethod
from moviepy import VideoFileClip
import numpy as np

class VideoEffect(ABC):
    """Base class for all video effects"""
    
    @abstractmethod
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply the effect to a video clip"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the effect"""
        pass

class BlurEffect(VideoEffect):
    def __init__(self, strength: float = 1.0):
        self.strength = strength
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply blur effect"""
        def blur_frame(get_frame, t):
            frame = get_frame(t)
            # Simple blur using convolution
            kernel_size = int(self.strength * 5)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            import cv2
            blurred = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
            return blurred
        
        return clip.fl(blur_frame)
    
    def get_name(self) -> str:
        return "Blur Effect"

class BrightnessEffect(VideoEffect):
    def __init__(self, brightness: float = 1.2):
        self.brightness = brightness
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply brightness adjustment"""
        def adjust_brightness(get_frame, t):
            frame = get_frame(t)
            # Adjust brightness
            bright_frame = np.clip(frame * self.brightness, 0, 255).astype(np.uint8)
            return bright_frame
        
        return clip.fl(adjust_brightness)
    
    def get_name(self) -> str:
        return "Brightness Effect"

class ContrastEffect(VideoEffect):
    def __init__(self, contrast: float = 1.5):
        self.contrast = contrast
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply contrast adjustment"""
        def adjust_contrast(get_frame, t):
            frame = get_frame(t)
            # Adjust contrast
            contrast_frame = np.clip((frame - 128) * self.contrast + 128, 0, 255).astype(np.uint8)
            return contrast_frame
        
        return clip.fl(adjust_contrast)
    
    def get_name(self) -> str:
        return "Contrast Effect"

class SepiaEffect(VideoEffect):
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply sepia tone effect"""
        def sepia_tone(get_frame, t):
            frame = get_frame(t)
            # Sepia transformation matrix
            sepia_matrix = np.array([
                [0.393, 0.769, 0.189],
                [0.349, 0.686, 0.168],
                [0.272, 0.534, 0.131]
            ])
            
            # Apply sepia transformation
            sepia_frame = frame @ sepia_matrix.T
            sepia_frame = np.clip(sepia_frame, 0, 255).astype(np.uint8)
            return sepia_frame
        
        return clip.fl(sepia_tone)
    
    def get_name(self) -> str:
        return "Sepia Effect"

class SharpenEffect(VideoEffect):
    def __init__(self, strength: float = 1.0):
        self.strength = strength
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply sharpen effect"""
        def sharpen_frame(get_frame, t):
            frame = get_frame(t)
            import cv2
            
            # Create sharpening kernel
            kernel = np.array([[-1, -1, -1],
                              [-1, 9 + self.strength, -1],
                              [-1, -1, -1]])
            
            # Apply sharpening
            sharpened = cv2.filter2D(frame, -1, kernel)
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            return sharpened
        
        return clip.fl(sharpen_frame)
    
    def get_name(self) -> str:
        return "Sharpen Effect"

class VignetteEffect(VideoEffect):
    def __init__(self, strength: float = 0.5):
        self.strength = strength
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply vignette effect"""
        def vignette_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Create vignette mask
            x = np.arange(w)
            y = np.arange(h)
            X, Y = np.meshgrid(x, y)
            
            # Center coordinates
            cx, cy = w // 2, h // 2
            
            # Distance from center
            distance = np.sqrt((X - cx)**2 + (Y - cy)**2)
            max_distance = np.sqrt(cx**2 + cy**2)
            
            # Create vignette
            vignette = 1 - (distance / max_distance) * self.strength
            vignette = np.clip(vignette, 0, 1)
            
            # Apply vignette to all channels
            vignetted_frame = frame.copy()
            for c in range(frame.shape[2]):
                vignetted_frame[:, :, c] = vignetted_frame[:, :, c] * vignette
            
            return vignetted_frame.astype(np.uint8)
        
        return clip.fl(vignette_frame)
    
    def get_name(self) -> str:
        return "Vignette Effect"

class NoiseEffect(VideoEffect):
    def __init__(self, amount: float = 0.1):
        self.amount = amount
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply noise effect"""
        def add_noise(get_frame, t):
            frame = get_frame(t)
            
            # Generate random noise
            noise = np.random.normal(0, self.amount * 255, frame.shape)
            
            # Add noise to frame
            noisy_frame = frame + noise
            noisy_frame = np.clip(noisy_frame, 0, 255).astype(np.uint8)
            
            return noisy_frame
        
        return clip.fl(add_noise)
    
    def get_name(self) -> str:
        return "Noise Effect"

class PixelateEffect(VideoEffect):
    def __init__(self, pixel_size: int = 10):
        self.pixel_size = pixel_size
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply pixelate effect"""
        def pixelate_frame(get_frame, t):
            frame = get_frame(t)
            import cv2
            
            h, w = frame.shape[:2]
            
            # Resize down and then up to create pixelated effect
            small_frame = cv2.resize(frame, (w // self.pixel_size, h // self.pixel_size), interpolation=cv2.INTER_NEAREST)
            pixelated_frame = cv2.resize(small_frame, (w, h), interpolation=cv2.INTER_NEAREST)
            
            return pixelated_frame
        
        return clip.fl(pixelate_frame)
    
    def get_name(self) -> str:
        return "Pixelate Effect"

class EdgeDetectionEffect(VideoEffect):
    def __init__(self, threshold1: int = 100, threshold2: int = 200):
        self.threshold1 = threshold1
        self.threshold2 = threshold2
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply edge detection effect"""
        def detect_edges(get_frame, t):
            frame = get_frame(t)
            import cv2
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, self.threshold1, self.threshold2)
            
            # Convert back to 3-channel
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            
            return edges_colored
        
        return clip.fl(detect_edges)
    
    def get_name(self) -> str:
        return "Edge Detection Effect"

class EffectsManager:
    """Manager for all available effects"""
    
    def __init__(self):
        self.effects = {
            'blur': BlurEffect,
            'brightness': BrightnessEffect,
            'contrast': ContrastEffect,
            'sepia': SepiaEffect,
            'sharpen': SharpenEffect,
            'vignette': VignetteEffect,
            'noise': NoiseEffect,
            'pixelate': PixelateEffect,
            'edge_detection': EdgeDetectionEffect
        }
        
        # Initialize 3D effects manager
        try:
            from .effects_3d import Effects3DManager
            self.effects_3d = Effects3DManager()
            # Add 3D effects to main effects registry
            for effect_name in self.effects_3d.list_effects():
                self.effects[effect_name] = None  # Placeholder, handled specially
        except ImportError:
            self.effects_3d = None
    
    def get_effect(self, effect_name: str, **kwargs) -> VideoEffect:
        """Get an effect instance by name"""
        if effect_name in self.effects:
            return self.effects[effect_name](**kwargs)
        else:
            raise ValueError(f"Effect '{effect_name}' not found")
    
    def list_effects(self) -> list:
        """List all available effects"""
        return list(self.effects.keys())
    
    def apply_effect(self, clip: VideoFileClip, effect_name: str, **kwargs) -> VideoFileClip:
        """Apply an effect to a clip"""
        # Check if it's a 3D effect
        if self.effects_3d and effect_name in self.effects_3d.list_effects():
            return self.effects_3d.apply_effect(clip, effect_name, **kwargs)
        else:
            effect = self.get_effect(effect_name, **kwargs)
            return effect.apply(clip)
