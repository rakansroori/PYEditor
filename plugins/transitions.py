"""
Video transitions plugin system
Smooth transitions between video clips
"""

from abc import ABC, abstractmethod
from moviepy import VideoFileClip, CompositeVideoClip
import numpy as np

class VideoTransition(ABC):
    """Base class for all video transitions"""
    
    @abstractmethod
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply transition between two clips"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the transition"""
        pass

class CrossfadeTransition(VideoTransition):
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply crossfade transition"""
        # Fade out first clip
        clip1_fade = clip1.fadeout(duration)
        
        # Fade in second clip and set start time
        clip2_fade = clip2.fadein(duration).with_start(clip1.duration - duration)
        
        # Composite the clips
        return CompositeVideoClip([clip1_fade, clip2_fade])
    
    def get_name(self) -> str:
        return "Crossfade"

class SlideTransition(VideoTransition):
    def __init__(self, direction: str = "left"):
        self.direction = direction
    
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply slide transition"""
        w, h = clip1.size
        
        if self.direction == "left":
            # Slide from right to left
            clip1_move = clip1.with_position(lambda t: (-w * t / duration, 0) if t <= duration else (-w, 0))
            clip2_move = clip2.with_position(lambda t: (w - w * t / duration, 0) if t <= duration else (0, 0))
        elif self.direction == "right":
            # Slide from left to right
            clip1_move = clip1.with_position(lambda t: (w * t / duration, 0) if t <= duration else (w, 0))
            clip2_move = clip2.with_position(lambda t: (-w + w * t / duration, 0) if t <= duration else (0, 0))
        elif self.direction == "up":
            # Slide from bottom to top
            clip1_move = clip1.with_position(lambda t: (0, -h * t / duration) if t <= duration else (0, -h))
            clip2_move = clip2.with_position(lambda t: (0, h - h * t / duration) if t <= duration else (0, 0))
        elif self.direction == "down":
            # Slide from top to bottom
            clip1_move = clip1.with_position(lambda t: (0, h * t / duration) if t <= duration else (0, h))
            clip2_move = clip2.with_position(lambda t: (0, -h + h * t / duration) if t <= duration else (0, 0))
        
        # Set timing
        clip2_move = clip2_move.with_start(clip1.duration - duration)
        
        return CompositeVideoClip([clip1_move, clip2_move])
    
    def get_name(self) -> str:
        return f"Slide {self.direction.capitalize()}"

class WipeTransition(VideoTransition):
    def __init__(self, direction: str = "horizontal"):
        self.direction = direction
    
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply wipe transition"""
        def wipe_effect(get_frame, t):
            if t < clip1.duration - duration:
                return clip1.get_frame(t)
            elif t >= clip1.duration:
                return clip2.get_frame(t - clip1.duration + duration)
            else:
                # Transition period
                progress = (t - (clip1.duration - duration)) / duration
                frame1 = clip1.get_frame(t)
                frame2 = clip2.get_frame(t - clip1.duration + duration)
                
                h, w = frame1.shape[:2]
                
                if self.direction == "horizontal":
                    # Horizontal wipe
                    split = int(w * progress)
                    result = frame1.copy()
                    result[:, :split] = frame2[:, :split]
                elif self.direction == "vertical":
                    # Vertical wipe
                    split = int(h * progress)
                    result = frame1.copy()
                    result[:split, :] = frame2[:split, :]
                
                return result
        
        total_duration = clip1.duration + clip2.duration - duration
        return VideoFileClip(make_frame=wipe_effect, duration=total_duration)
    
    def get_name(self) -> str:
        return f"Wipe {self.direction.capitalize()}"

class FadeToBlackTransition(VideoTransition):
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply fade to black transition"""
        # Fade out first clip to black
        clip1_fade = clip1.fadeout(duration)
        
        # Fade in second clip from black
        clip2_fade = clip2.fadein(duration).with_start(clip1.duration)
        
        # Create black frame for the gap
        from moviepy import ColorClip
        black_clip = ColorClip(size=clip1.size, color=(0, 0, 0), duration=duration).with_start(clip1.duration - duration)
        
        return CompositeVideoClip([clip1_fade, black_clip, clip2_fade])
    
    def get_name(self) -> str:
        return "Fade to Black"

class ZoomTransition(VideoTransition):
    def __init__(self, zoom_type: str = "in"):
        self.zoom_type = zoom_type
    
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply zoom transition"""
        w, h = clip1.size
        
        if self.zoom_type == "in":
            # Zoom in on first clip, zoom out on second
            clip1_zoom = clip1.resize(lambda t: 1 + (t/duration) * 0.5 if t <= duration else 1.5)
            clip2_zoom = clip2.resize(lambda t: 1.5 - (t/duration) * 0.5 if t <= duration else 1.0)
        else:
            # Zoom out on first clip, zoom in on second
            clip1_zoom = clip1.resize(lambda t: 1 - (t/duration) * 0.5 if t <= duration else 0.5)
            clip2_zoom = clip2.resize(lambda t: 0.5 + (t/duration) * 0.5 if t <= duration else 1.0)
        
        # Apply crossfade
        clip1_fade = clip1_zoom.fadeout(duration)
        clip2_fade = clip2_zoom.fadein(duration).with_start(clip1.duration - duration)
        
        return CompositeVideoClip([clip1_fade, clip2_fade])
    
    def get_name(self) -> str:
        return f"Zoom {self.zoom_type.capitalize()}"

class CircularWipeTransition(VideoTransition):
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply circular wipe transition"""
        def circular_wipe_effect(get_frame, t):
            if t < clip1.duration - duration:
                return clip1.get_frame(t)
            elif t >= clip1.duration:
                return clip2.get_frame(t - clip1.duration + duration)
            else:
                # Transition period
                progress = (t - (clip1.duration - duration)) / duration
                frame1 = clip1.get_frame(t)
                frame2 = clip2.get_frame(t - clip1.duration + duration)
                
                h, w = frame1.shape[:2]
                cx, cy = w // 2, h // 2
                
                # Create circular mask
                y, x = np.ogrid[:h, :w]
                mask = (x - cx)**2 + (y - cy)**2 <= (progress * max(w, h))**2
                
                result = frame1.copy()
                result[mask] = frame2[mask]
                
                return result
        
        total_duration = clip1.duration + clip2.duration - duration
        return VideoFileClip(make_frame=circular_wipe_effect, duration=total_duration)
    
    def get_name(self) -> str:
        return "Circular Wipe"

class PushTransition(VideoTransition):
    def __init__(self, direction: str = "left"):
        self.direction = direction
    
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply push transition"""
        w, h = clip1.size
        
        if self.direction == "left":
            # Push from right
            clip1_move = clip1.with_position(lambda t: (-w * t / duration, 0) if t <= duration else (-w, 0))
            clip2_move = clip2.with_position(lambda t: (w - w * t / duration, 0) if t <= duration else (0, 0))
        elif self.direction == "right":
            # Push from left
            clip1_move = clip1.with_position(lambda t: (w * t / duration, 0) if t <= duration else (w, 0))
            clip2_move = clip2.with_position(lambda t: (-w + w * t / duration, 0) if t <= duration else (0, 0))
        elif self.direction == "up":
            # Push from bottom
            clip1_move = clip1.with_position(lambda t: (0, -h * t / duration) if t <= duration else (0, -h))
            clip2_move = clip2.with_position(lambda t: (0, h - h * t / duration) if t <= duration else (0, 0))
        elif self.direction == "down":
            # Push from top
            clip1_move = clip1.with_position(lambda t: (0, h * t / duration) if t <= duration else (0, h))
            clip2_move = clip2.with_position(lambda t: (0, -h + h * t / duration) if t <= duration else (0, 0))
        
        # Set timing
        clip2_move = clip2_move.with_start(clip1.duration - duration)
        
        return CompositeVideoClip([clip1_move, clip2_move], size=(w, h))
    
    def get_name(self) -> str:
        return f"Push {self.direction.capitalize()}"

class RotateTransition(VideoTransition):
    def apply(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Apply rotate transition"""
        # Rotate first clip out, second clip in
        clip1_rotate = clip1.rotate(lambda t: (t/duration) * 180 if t <= duration else 180)
        clip2_rotate = clip2.rotate(lambda t: 180 - (t/duration) * 180 if t <= duration else 0)
        
        # Apply crossfade
        clip1_fade = clip1_rotate.fadeout(duration)
        clip2_fade = clip2_rotate.fadein(duration).with_start(clip1.duration - duration)
        
        return CompositeVideoClip([clip1_fade, clip2_fade])
    
    def get_name(self) -> str:
        return "Rotate"

class TransitionsManager:
    """Manager for all available transitions"""
    
    def __init__(self):
        self.transitions = {
            'crossfade': CrossfadeTransition,
            'slide_left': lambda: SlideTransition("left"),
            'slide_right': lambda: SlideTransition("right"),
            'slide_up': lambda: SlideTransition("up"),
            'slide_down': lambda: SlideTransition("down"),
            'wipe_horizontal': lambda: WipeTransition("horizontal"),
            'wipe_vertical': lambda: WipeTransition("vertical"),
            'fade_to_black': FadeToBlackTransition,
            'zoom_in': lambda: ZoomTransition("in"),
            'zoom_out': lambda: ZoomTransition("out"),
            'circular_wipe': CircularWipeTransition,
            'push_left': lambda: PushTransition("left"),
            'push_right': lambda: PushTransition("right"),
            'push_up': lambda: PushTransition("up"),
            'push_down': lambda: PushTransition("down"),
            'rotate': RotateTransition
        }
    
    def get_transition(self, transition_name: str) -> VideoTransition:
        """Get a transition instance by name"""
        if transition_name in self.transitions:
            return self.transitions[transition_name]()
        else:
            raise ValueError(f"Transition '{transition_name}' not found")
    
    def list_transitions(self) -> list:
        """List all available transitions"""
        return list(self.transitions.keys())
    
    def apply_transition(self, clip1: VideoFileClip, clip2: VideoFileClip, 
                        transition_name: str, duration: float) -> VideoFileClip:
        """Apply a transition between two clips"""
        transition = self.get_transition(transition_name)
        return transition.apply(clip1, clip2, duration)
