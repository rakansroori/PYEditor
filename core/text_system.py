"""
Title and Text System for video editing
Handles text overlays, animations, styling, and motion graphics templates
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import os
try:
    from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
    from moviepy.video.fx import Resize, FadeOut, FadeIn
except ImportError:
    try:
        from moviepy import TextClip, CompositeVideoClip, ColorClip
        from moviepy.video.fx import Resize, FadeOut, FadeIn
    except ImportError:
        # Create dummy classes if MoviePy is not available (for testing)
        class TextClip:
            pass
        class CompositeVideoClip:
            pass
        class ColorClip:
            pass
        class Resize:
            pass
        class FadeOut:
            pass
        class FadeIn:
            pass

class TextAnimation(Enum):
    """Text animation types"""
    NONE = "none"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    TYPEWRITER = "typewriter"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    BOUNCE = "bounce"
    ROTATE_IN = "rotate_in"
    GLOW = "glow"

class TextAlignment(Enum):
    """Text alignment options"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"

@dataclass
class TextStyle:
    """Text styling configuration"""
    font: str = "Arial"
    font_size: int = 48
    color: str = "white"
    stroke_color: Optional[str] = None
    stroke_width: int = 0
    background_color: Optional[str] = None
    shadow_color: Optional[str] = None
    shadow_offset: Tuple[int, int] = (2, 2)
    alignment: TextAlignment = TextAlignment.CENTER
    line_spacing: float = 1.2
    letter_spacing: float = 0.0
    bold: bool = False
    italic: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'font': self.font,
            'font_size': self.font_size,
            'color': self.color,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'background_color': self.background_color,
            'shadow_color': self.shadow_color,
            'shadow_offset': self.shadow_offset,
            'alignment': self.alignment.value,
            'line_spacing': self.line_spacing,
            'letter_spacing': self.letter_spacing,
            'bold': self.bold,
            'italic': self.italic
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextStyle':
        """Create from dictionary"""
        style = cls()
        for key, value in data.items():
            if key == 'alignment':
                value = TextAlignment(value)
            setattr(style, key, value)
        return style

@dataclass
class TextAnimationConfig:
    """Text animation configuration"""
    animation_type: TextAnimation = TextAnimation.NONE
    duration: float = 1.0
    delay: float = 0.0
    easing: str = "ease_in_out"  # ease_in, ease_out, ease_in_out, linear
    repeat: int = 1
    reverse: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'animation_type': self.animation_type.value,
            'duration': self.duration,
            'delay': self.delay,
            'easing': self.easing,
            'repeat': self.repeat,
            'reverse': self.reverse
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextAnimationConfig':
        """Create from dictionary"""
        config = cls()
        for key, value in data.items():
            if key == 'animation_type':
                value = TextAnimation(value)
            setattr(config, key, value)
        return config

class TextClipGenerator:
    """Generates text clips with styling and animations"""
    
    def __init__(self):
        self.available_fonts = self._get_available_fonts()
        self.default_style = TextStyle()
    
    def _get_available_fonts(self) -> List[str]:
        """Get list of available system fonts"""
        # Basic font list - could be expanded with system font detection
        return [
            "Arial", "Times New Roman", "Helvetica", "Verdana", "Courier New",
            "Georgia", "Trebuchet MS", "Comic Sans MS", "Impact", "Lucida Console",
            "Palatino", "Tahoma", "Century Gothic", "Franklin Gothic Medium"
        ]
    
    def create_text_clip(self, text: str, style: TextStyle, duration: float = 3.0) -> TextClip:
        """Create a basic text clip with styling"""
        try:
            # Prepare font string
            font_style = style.font
            if style.bold and style.italic:
                font_style += "-Bold-Italic"
            elif style.bold:
                font_style += "-Bold" 
            elif style.italic:
                font_style += "-Italic"
            
            # Create text clip with better font handling
            clip = TextClip(
                text=text,
                font_size=style.font_size,
                color=style.color,
                font=None,  # Use default font to avoid font errors
                stroke_color=style.stroke_color,
                stroke_width=style.stroke_width,
                method='caption' if len(text) > 50 else 'label'
            ).with_duration(duration)
            
            # Apply background if specified
            if style.background_color:
                bg_clip = ColorClip(
                    size=clip.size, 
                    color=style.background_color
                ).with_duration(duration)
                clip = CompositeVideoClip([bg_clip, clip])
            
            return clip
            
        except Exception as e:
            print(f"Error creating text clip: {e}")
            # Fallback to basic text clip
            return TextClip(
                text=text,
                font_size=style.font_size,
                color=style.color
            ).with_duration(duration)
    
    def apply_animation(self, clip: TextClip, animation: TextAnimationConfig) -> TextClip:
        """Apply animation to text clip"""
        try:
            animated_clip = clip
            
            if animation.animation_type == TextAnimation.FADE_IN:
                animated_clip = clip.with_fx(FadeIn, animation.duration)
            
            elif animation.animation_type == TextAnimation.FADE_OUT:
                animated_clip = clip.with_fx(FadeOut, animation.duration)
            
            elif animation.animation_type == TextAnimation.SCALE_IN:
                # Scale from 0 to full size
                def scale_effect(get_frame, t):
                    if t < animation.duration:
                        scale = t / animation.duration
                        if scale > 0:
                            return clip.with_fx(Resize, scale).get_frame(t)
                    return get_frame(t)
                animated_clip = clip.fl(scale_effect)
            
            elif animation.animation_type == TextAnimation.SLIDE_LEFT:
                # Slide in from right
                def slide_effect(get_frame, t):
                    if t < animation.duration:
                        offset = int((1 - t / animation.duration) * clip.w)
                        return clip.with_position((offset, 'center'))(get_frame, t)
                    return clip.with_position('center')(get_frame, t)
                animated_clip = clip.fl(slide_effect)
            
            elif animation.animation_type == TextAnimation.SLIDE_RIGHT:
                # Slide in from left
                def slide_effect(get_frame, t):
                    if t < animation.duration:
                        offset = int((t / animation.duration - 1) * clip.w)
                        return clip.with_position((offset, 'center'))(get_frame, t)
                    return clip.with_position('center')(get_frame, t)
                animated_clip = clip.fl(slide_effect)
            
            elif animation.animation_type == TextAnimation.TYPEWRITER:
                # Typewriter effect - reveal characters progressively
                def typewriter_effect(get_frame, t):
                    if t < animation.duration:
                        chars_to_show = int((t / animation.duration) * len(clip.txt))
                        partial_text = clip.txt[:chars_to_show]
                        if partial_text:
                            return TextClip(
                                partial_text,
                                font_size=clip.font_size,
                                color=clip.color,
                                font=clip.font
                            ).with_duration(clip.duration)(get_frame, 0)
                    return get_frame(t)
                animated_clip = clip.fl(typewriter_effect)
            
            # Apply delay if specified
            if animation.delay > 0:
                animated_clip = animated_clip.with_start(animation.delay)
            
            return animated_clip
            
        except Exception as e:
            print(f"Error applying animation: {e}")
            return clip

class TextTemplate:
    """Template for text styling and animation presets"""
    
    def __init__(self, name: str, style: TextStyle, animation: TextAnimationConfig):
        self.name = name
        self.style = style
        self.animation = animation
        self.description = ""
        self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            'name': self.name,
            'style': self.style.to_dict(),
            'animation': self.animation.to_dict(),
            'description': self.description,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextTemplate':
        """Create template from dictionary"""
        template = cls(
            name=data['name'],
            style=TextStyle.from_dict(data['style']),
            animation=TextAnimationConfig.from_dict(data['animation'])
        )
        template.description = data.get('description', '')
        template.tags = data.get('tags', [])
        return template

class TitleSystem:
    """Main title and text system manager"""
    
    def __init__(self):
        self.clip_generator = TextClipGenerator()
        self.templates: Dict[str, TextTemplate] = {}
        self.text_clips: Dict[str, Dict] = {}  # Store created text clips
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default text templates"""
        # Title templates
        self.templates['main_title'] = TextTemplate(
            name="Main Title",
            style=TextStyle(
                font="Arial",
                font_size=72,
                color="white",
                stroke_color="black",
                stroke_width=2,
                bold=True
            ),
            animation=TextAnimationConfig(
                animation_type=TextAnimation.FADE_IN,
                duration=1.0
            )
        )
        
        self.templates['subtitle'] = TextTemplate(
            name="Subtitle",
            style=TextStyle(
                font="Arial",
                font_size=36,
                color="yellow",
                alignment=TextAlignment.CENTER
            ),
            animation=TextAnimationConfig(
                animation_type=TextAnimation.SLIDE_UP,
                duration=0.8
            )
        )
        
        self.templates['lower_third'] = TextTemplate(
            name="Lower Third",
            style=TextStyle(
                font="Arial",
                font_size=28,
                color="white",
                background_color="rgba(0,0,0,0.7)",
                alignment=TextAlignment.LEFT
            ),
            animation=TextAnimationConfig(
                animation_type=TextAnimation.SLIDE_LEFT,
                duration=0.5
            )
        )
        
        self.templates['typewriter_title'] = TextTemplate(
            name="Typewriter Title",
            style=TextStyle(
                font="Courier New",
                font_size=48,
                color="green"
            ),
            animation=TextAnimationConfig(
                animation_type=TextAnimation.TYPEWRITER,
                duration=2.0
            )
        )
        
        self.templates['impact_title'] = TextTemplate(
            name="Impact Title",
            style=TextStyle(
                font="Impact",
                font_size=84,
                color="red",
                stroke_color="white",
                stroke_width=3,
                bold=True
            ),
            animation=TextAnimationConfig(
                animation_type=TextAnimation.SCALE_IN,
                duration=0.6
            )
        )
    
    def create_text_overlay(self, text: str, template_name: str = None, 
                           custom_style: TextStyle = None, 
                           custom_animation: TextAnimationConfig = None,
                           duration: float = 3.0,
                           position: Tuple[str, str] = ('center', 'center')) -> Dict:
        """Create a text overlay with specified styling and animation"""
        
        # Use template or custom styling
        if template_name and template_name in self.templates:
            template = self.templates[template_name]
            style = custom_style or template.style
            animation = custom_animation or template.animation
        else:
            style = custom_style or self.clip_generator.default_style
            animation = custom_animation or TextAnimationConfig()
        
        # Create text clip
        text_clip = self.clip_generator.create_text_clip(text, style, duration)
        
        # Apply animation
        if animation.animation_type != TextAnimation.NONE:
            text_clip = self.clip_generator.apply_animation(text_clip, animation)
        
        # Set position
        text_clip = text_clip.with_position(position)
        
        # Store clip info
        clip_id = f"text_{len(self.text_clips)}"
        self.text_clips[clip_id] = {
            'clip': text_clip,
            'text': text,
            'style': style,
            'animation': animation,
            'duration': duration,
            'position': position
        }
        
        return {
            'id': clip_id,
            'clip': text_clip,
            'text': text,
            'duration': duration
        }
    
    def get_template(self, name: str) -> Optional[TextTemplate]:
        """Get template by name"""
        return self.templates.get(name)
    
    def add_template(self, template: TextTemplate):
        """Add custom template"""
        self.templates[template.name] = template
    
    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.templates.keys())
    
    def save_templates(self, filepath: str):
        """Save templates to file"""
        try:
            templates_data = {
                name: template.to_dict() 
                for name, template in self.templates.items()
            }
            with open(filepath, 'w') as f:
                json.dump(templates_data, f, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")
    
    def load_templates(self, filepath: str):
        """Load templates from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    templates_data = json.load(f)
                
                for name, data in templates_data.items():
                    template = TextTemplate.from_dict(data)
                    self.templates[name] = template
        except Exception as e:
            print(f"Error loading templates: {e}")
    
    def create_title_sequence(self, titles: List[Dict], total_duration: float = 10.0) -> CompositeVideoClip:
        """Create a title sequence with multiple text elements"""
        clips = []
        
        for i, title_config in enumerate(titles):
            text = title_config.get('text', f'Title {i+1}')
            template = title_config.get('template', 'main_title')
            start_time = title_config.get('start_time', i * 2.0)
            duration = title_config.get('duration', 3.0)
            position = title_config.get('position', ('center', 'center'))
            
            # Create text overlay
            overlay = self.create_text_overlay(
                text=text,
                template_name=template,
                duration=duration,
                position=position
            )
            
            # Set start time
            clip = overlay['clip'].with_start(start_time)
            clips.append(clip)
        
        # Create background if needed
        if clips:
            # Use first clip size as reference
            bg_size = clips[0].size
            background = ColorClip(
                size=bg_size,
                color=(0, 0, 0)  # Black background
            ).with_duration(total_duration)
            
            clips.insert(0, background)
        
        return CompositeVideoClip(clips)
    
    def get_text_clip(self, clip_id: str) -> Optional[Dict]:
        """Get text clip by ID"""
        return self.text_clips.get(clip_id)
    
    def update_text_style(self, clip_id: str, new_style: TextStyle) -> bool:
        """Update text clip styling"""
        if clip_id not in self.text_clips:
            return False
        
        try:
            clip_info = self.text_clips[clip_id]
            
            # Create new clip with updated style
            new_clip = self.clip_generator.create_text_clip(
                clip_info['text'], 
                new_style, 
                clip_info['duration']
            )
            
            # Apply existing animation
            if clip_info['animation'].animation_type != TextAnimation.NONE:
                new_clip = self.clip_generator.apply_animation(new_clip, clip_info['animation'])
            
            # Update stored clip
            clip_info['clip'] = new_clip.with_position(clip_info['position'])
            clip_info['style'] = new_style
            
            return True
        except Exception as e:
            print(f"Error updating text style: {e}")
            return False
