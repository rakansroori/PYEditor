"""
Export Presets for PyVideoEditor
Provides predefined export configurations for various platforms and use cases
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
import os

@dataclass
class ExportPreset:
    """Represents an export preset with all necessary parameters"""
    name: str
    description: str
    category: str
    
    # Video settings
    resolution: Tuple[int, int]  # (width, height)
    fps: float
    video_codec: str
    video_bitrate: str
    
    # Audio settings
    audio_codec: str
    audio_bitrate: str
    audio_sample_rate: int
    
    # Container format
    container: str
    file_extension: str
    
    # Advanced settings
    preset_speed: str = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    profile: str = "high"
    level: str = "4.0"
    pixel_format: str = "yuv420p"
    
    # Optional settings
    max_bitrate: Optional[str] = None
    buffer_size: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert preset to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'resolution': self.resolution,
            'fps': self.fps,
            'video_codec': self.video_codec,
            'video_bitrate': self.video_bitrate,
            'audio_codec': self.audio_codec,
            'audio_bitrate': self.audio_bitrate,
            'audio_sample_rate': self.audio_sample_rate,
            'container': self.container,
            'file_extension': self.file_extension,
            'preset_speed': self.preset_speed,
            'profile': self.profile,
            'level': self.level,
            'pixel_format': self.pixel_format,
            'max_bitrate': self.max_bitrate,
            'buffer_size': self.buffer_size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExportPreset':
        """Create preset from dictionary"""
        return cls(**data)

class ExportPresetsManager:
    """Manages export presets for the video editor"""
    
    def __init__(self):
        self.presets: Dict[str, ExportPreset] = {}
        self.load_default_presets()
    
    def load_default_presets(self):
        """Load default export presets"""
        # YouTube presets
        self.add_preset(ExportPreset(
            name="YouTube 1080p",
            description="Optimized for YouTube uploads - Full HD quality",
            category="YouTube",
            resolution=(1920, 1080),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="8000k",
            audio_codec="aac",
            audio_bitrate="192k",
            audio_sample_rate=48000,
            container="mp4",
            file_extension=".mp4",
            preset_speed="medium",
            profile="high",
            level="4.2"
        ))
        
        self.add_preset(ExportPreset(
            name="YouTube 4K",
            description="4K Ultra HD for YouTube - Premium quality",
            category="YouTube",
            resolution=(3840, 2160),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="35000k",
            audio_codec="aac",
            audio_bitrate="192k",
            audio_sample_rate=48000,
            container="mp4",
            file_extension=".mp4",
            preset_speed="slow",
            profile="high",
            level="5.2",
            max_bitrate="53000k",
            buffer_size="106000k"
        ))
        
        self.add_preset(ExportPreset(
            name="YouTube 720p",
            description="HD quality for YouTube - Good balance of quality and file size",
            category="YouTube",
            resolution=(1280, 720),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="5000k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=48000,
            container="mp4",
            file_extension=".mp4",
            preset_speed="medium",
            profile="high",
            level="4.0"
        ))
        
        # Instagram presets
        self.add_preset(ExportPreset(
            name="Instagram Post",
            description="Square format for Instagram posts",
            category="Instagram",
            resolution=(1080, 1080),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="3500k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="high",
            level="4.0"
        ))
        
        self.add_preset(ExportPreset(
            name="Instagram Stories",
            description="Vertical format for Instagram Stories",
            category="Instagram",
            resolution=(1080, 1920),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="3500k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="high",
            level="4.0"
        ))
        
        self.add_preset(ExportPreset(
            name="Instagram Reels",
            description="Optimized for Instagram Reels",
            category="Instagram",
            resolution=(1080, 1920),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="2500k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="main",
            level="4.0"
        ))
        
        # TikTok presets
        self.add_preset(ExportPreset(
            name="TikTok",
            description="Vertical format optimized for TikTok",
            category="TikTok",
            resolution=(1080, 1920),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="2500k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="main",
            level="4.0"
        ))
        
        # Twitter/X presets
        self.add_preset(ExportPreset(
            name="Twitter Video",
            description="Optimized for Twitter/X video posts",
            category="Twitter",
            resolution=(1280, 720),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="2500k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="main",
            level="3.1"
        ))
        
        # Facebook presets
        self.add_preset(ExportPreset(
            name="Facebook Video",
            description="Standard Facebook video upload",
            category="Facebook",
            resolution=(1920, 1080),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="4000k",
            audio_codec="aac",
            audio_bitrate="128k",
            audio_sample_rate=48000,
            container="mp4",
            file_extension=".mp4",
            preset_speed="medium",
            profile="high",
            level="4.0"
        ))
        
        # General presets
        self.add_preset(ExportPreset(
            name="High Quality",
            description="High quality export for archival or further editing",
            category="General",
            resolution=(1920, 1080),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="15000k",
            audio_codec="aac",
            audio_bitrate="256k",
            audio_sample_rate=48000,
            container="mp4",
            file_extension=".mp4",
            preset_speed="slow",
            profile="high",
            level="4.2"
        ))
        
        self.add_preset(ExportPreset(
            name="Web Optimized",
            description="Small file size for web streaming",
            category="General",
            resolution=(1280, 720),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="1500k",
            audio_codec="aac",
            audio_bitrate="96k",
            audio_sample_rate=44100,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="main",
            level="3.1"
        ))
        
        self.add_preset(ExportPreset(
            name="Mobile Friendly",
            description="Optimized for mobile devices - small file size",
            category="General",
            resolution=(854, 480),
            fps=30.0,
            video_codec="libx264",
            video_bitrate="1000k",
            audio_codec="aac",
            audio_bitrate="64k",
            audio_sample_rate=22050,
            container="mp4",
            file_extension=".mp4",
            preset_speed="fast",
            profile="baseline",
            level="3.0"
        ))
        
        # Professional presets
        self.add_preset(ExportPreset(
            name="ProRes Proxy",
            description="Apple ProRes 422 Proxy for editing",
            category="Professional",
            resolution=(1920, 1080),
            fps=30.0,
            video_codec="prores",
            video_bitrate="45000k",
            audio_codec="pcm_s16le",
            audio_bitrate="1536k",
            audio_sample_rate=48000,
            container="mov",
            file_extension=".mov",
            preset_speed="medium",
            profile="proxy",
            level="4.0"
        ))
        
        # DVD/Broadcast presets
        self.add_preset(ExportPreset(
            name="DVD NTSC",
            description="DVD quality NTSC format",
            category="Broadcast",
            resolution=(720, 480),
            fps=29.97,
            video_codec="mpeg2video",
            video_bitrate="6000k",
            audio_codec="ac3",
            audio_bitrate="192k",
            audio_sample_rate=48000,
            container="mpeg",
            file_extension=".mpg",
            preset_speed="medium",
            profile="main",
            level="ML"
        ))
        
        self.add_preset(ExportPreset(
            name="DVD PAL",
            description="DVD quality PAL format",
            category="Broadcast",
            resolution=(720, 576),
            fps=25.0,
            video_codec="mpeg2video",
            video_bitrate="6000k",
            audio_codec="ac3",
            audio_bitrate="192k",
            audio_sample_rate=48000,
            container="mpeg",
            file_extension=".mpg",
            preset_speed="medium",
            profile="main",
            level="ML"
        ))
    
    def add_preset(self, preset: ExportPreset):
        """Add a preset to the manager"""
        self.presets[preset.name] = preset
    
    def get_preset(self, name: str) -> Optional[ExportPreset]:
        """Get a preset by name"""
        return self.presets.get(name)
    
    def get_presets_by_category(self, category: str) -> List[ExportPreset]:
        """Get all presets in a specific category"""
        return [preset for preset in self.presets.values() if preset.category == category]
    
    def get_all_presets(self) -> List[ExportPreset]:
        """Get all available presets"""
        return list(self.presets.values())
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        categories = set(preset.category for preset in self.presets.values())
        return sorted(list(categories))
    
    def save_presets(self, filepath: str):
        """Save all presets to a JSON file"""
        presets_data = {name: preset.to_dict() for name, preset in self.presets.items()}
        with open(filepath, 'w') as f:
            json.dump(presets_data, f, indent=2)
    
    def load_presets(self, filepath: str):
        """Load presets from a JSON file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                presets_data = json.load(f)
            
            for name, data in presets_data.items():
                preset = ExportPreset.from_dict(data)
                self.presets[name] = preset
    
    def create_custom_preset(self, name: str, description: str, category: str = "Custom", **kwargs) -> ExportPreset:
        """Create a custom preset"""
        # Set default values for required parameters
        defaults = {
            'resolution': (1920, 1080),
            'fps': 30.0,
            'video_codec': 'libx264',
            'video_bitrate': '4000k',
            'audio_codec': 'aac',
            'audio_bitrate': '128k',
            'audio_sample_rate': 48000,
            'container': 'mp4',
            'file_extension': '.mp4'
        }
        
        # Update defaults with provided values
        defaults.update(kwargs)
        
        preset = ExportPreset(
            name=name,
            description=description,
            category=category,
            **defaults
        )
        
        self.add_preset(preset)
        return preset
    
    def remove_preset(self, name: str) -> bool:
        """Remove a preset by name"""
        if name in self.presets:
            del self.presets[name]
            return True
        return False
    
    def get_preset_names(self) -> List[str]:
        """Get all preset names"""
        return list(self.presets.keys())
    
    def list_presets(self) -> List[str]:
        """Get all preset names (alias for get_preset_names)"""
        return self.get_preset_names()
    
    def estimate_file_size(self, preset: ExportPreset, duration_seconds: float) -> dict:
        """Estimate output file size based on preset and duration"""
        try:
            # Extract bitrate values (remove 'k' suffix and convert to int)
            video_bitrate_kbps = int(preset.video_bitrate.replace('k', ''))
            audio_bitrate_kbps = int(preset.audio_bitrate.replace('k', ''))
            
            # Calculate total bitrate
            total_bitrate_kbps = video_bitrate_kbps + audio_bitrate_kbps
            
            # Calculate file size in bytes
            file_size_bytes = (total_bitrate_kbps * 1000 * duration_seconds) / 8
            
            # Convert to different units
            file_size_kb = file_size_bytes / 1024
            file_size_mb = file_size_kb / 1024
            file_size_gb = file_size_mb / 1024
            
            return {
                'bytes': int(file_size_bytes),
                'kb': round(file_size_kb, 2),
                'mb': round(file_size_mb, 2),
                'gb': round(file_size_gb, 3),
                'formatted': self._format_file_size(file_size_bytes)
            }
        except (ValueError, AttributeError):
            return {'error': 'Could not estimate file size'}
    
    def _format_file_size(self, size_bytes: float) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{int(size_bytes)} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
