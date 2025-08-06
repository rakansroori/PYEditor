"""
Core video processing module using MoviePy and OpenCV
Handles video loading, editing, effects, and export functionality
"""

import cv2
import numpy as np
from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips, vfx
from typing import Optional, List, Tuple
import os
from .export_presets import ExportPreset, ExportPresetsManager
from .color_grading import ColorGrading
from .audio_editing import AudioProcessor, AudioEffectsManager
from plugins.effects import EffectsManager
from plugins.transitions import TransitionsManager
from .chroma_key import ChromaKeyManager
from .text_system import TitleSystem

class VideoProcessor:
    def __init__(self):
        self.clips: List[VideoFileClip] = []
        self.current_clip: Optional[VideoFileClip] = None
        self.timeline_clips: List[dict] = []
        self.color_grading = ColorGrading()
        self.audio_processor = AudioProcessor()
        self.audio_effects = AudioEffectsManager()
        self.chroma_key_manager = ChromaKeyManager()
        self.title_system = TitleSystem()
        self.effects_manager = EffectsManager()
        self.transitions_manager = TransitionsManager()
        self.export_presets_manager = ExportPresetsManager()
        
    def load_video(self, file_path: str) -> bool:
        """Load a video file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Video file not found: {file_path}")
                
            clip = VideoFileClip(file_path)
            self.current_clip = clip
            self.clips.append(clip)
            
            print(f"Loaded video: {file_path}")
            print(f"Duration: {clip.duration:.2f}s")
            print(f"FPS: {clip.fps}")
            print(f"Size: {clip.size}")
            
            return True
            
        except Exception as e:
            print(f"Error loading video: {e}")
            return False
    
    def get_frame_at_time(self, time: float) -> Optional[np.ndarray]:
        """Get a frame at specific time"""
        if not self.current_clip:
            return None
            
        try:
            frame = self.current_clip.get_frame(time)
            return frame
        except Exception as e:
            print(f"Error getting frame: {e}")
            return None
    
    def trim_clip(self, start_time: float, end_time: float) -> Optional[VideoFileClip]:
        """Trim current clip between start and end times"""
        if not self.current_clip:
            return None
            
        try:
            trimmed = self.current_clip.subclip(start_time, end_time)
            return trimmed
        except Exception as e:
            print(f"Error trimming clip: {e}")
            return None
    
    def apply_fadein(self, duration: float):
        """Apply fade-in effect."""
        if self.current_clip:
            self.current_clip = self.current_clip.fx(vfx.fadein, duration)

    def apply_fadeout(self, duration: float):
        """Apply fade-out effect."""
        if self.current_clip:
            self.current_clip = self.current_clip.fx(vfx.fadeout, duration)

    def crossfade_clips(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float) -> VideoFileClip:
        """Crossfade between two clips."""
        return concatenate_videoclips(
            [clip1.crossfadein(duration), clip2.with_start(clip1.duration).crossfadein(duration)],
            method="compose"
        )

    def add_to_timeline(self, clip: VideoFileClip, start_time: float = 0):
        """Add clip to timeline at specified time"""
        self.timeline_clips.append({
            'clip': clip,
            'start_time': start_time,
            'duration': clip.duration
        })

    def export_video_with_preset(self, output_path: str, preset_name: str) -> bool:
        """Export the final video using a specific preset"""
        if not self.timeline_clips:
            print("No clips in timeline to export")
            return False
            
        preset = self.export_presets_manager.get_preset(preset_name)
        if not preset:
            print(f"Preset not found: {preset_name}")
            return False
        
        try:
            # Sort clips by start time
            sorted_clips = sorted(self.timeline_clips, key=lambda x: x['start_time'])
            
            # Create composite video
            clips_for_export = [item['clip'] for item in sorted_clips]
            final_video = concatenate_videoclips(clips_for_export)
            
            # Export with preset settings
            final_video.write_videofile(
                output_path,
                codec=preset.video_codec,
                audio_codec=preset.audio_codec,
                audio_bitrate=preset.audio_bitrate,
                bitrate=preset.video_bitrate,
                fps=preset.fps,
                preset=preset.preset_speed,
                ffmpeg_params=[
                    '-profile:v', preset.profile,
                    '-level', preset.level,
                    '-pix_fmt', preset.pixel_format
                ],
                threads=4,
                verbose=True,
                logger='bar'
            )
            
            print(f"Video exported to: {output_path} with preset: {preset.name}")
            return True
            
        except Exception as e:
            print(f"Error exporting video with preset: {e}")
            return False
    
    def apply_effect_to_clip(self, clip: VideoFileClip, effect_name: str, **kwargs) -> VideoFileClip:
        """Apply specified effect to a video clip"""
        return self.effects_manager.apply_effect(clip, effect_name, **kwargs)

    def apply_transition_between_clips(self, clip1: VideoFileClip, clip2: VideoFileClip, transition_name: str, duration: float) -> VideoFileClip:
        """Apply specified transition between two video clips"""
        return self.transitions_manager.apply_transition(clip1, clip2, transition_name, duration)

    def list_available_effects(self) -> list:
        """List all available video effects"""
        return self.effects_manager.list_effects()

    def list_available_transitions(self) -> list:
        """List all available video transitions"""
        return self.transitions_manager.list_transitions()

    def get_video_info(self) -> dict:
        """Get information about current video"""
        if not self.current_clip:
            return {}
            
        return {
            'duration': self.current_clip.duration,
            'fps': self.current_clip.fps,
            'size': self.current_clip.size,
            'has_audio': self.current_clip.audio is not None
        }
    
    def apply_color_grading(self, hue_shift: float = 0, saturation_factor: float = 1.0, luminance_factor: float = 1.0):
        """Apply color grading to current clip"""
        if not self.current_clip:
            return False
            
        try:
            clip = self.current_clip
            
            if hue_shift != 0:
                clip = self.color_grading.adjust_hue(clip, hue_shift)
            
            if saturation_factor != 1.0:
                clip = self.color_grading.adjust_saturation(clip, saturation_factor)
            
            if luminance_factor != 1.0:
                clip = self.color_grading.adjust_luminance(clip, luminance_factor)
            
            self.current_clip = clip
            return True
            
        except Exception as e:
            print(f"Error applying color grading: {e}")
            return False
    
    def add_text_overlay(self, text: str, template_name: str = 'main_title', 
                        duration: float = 3.0, position: Tuple[str, str] = ('center', 'center')) -> bool:
        """Add text overlay to current clip"""
        if not self.current_clip:
            print("No video loaded")
            return False
            
        try:
            # Create text overlay
            text_overlay = self.title_system.create_text_overlay(
                text=text,
                template_name=template_name,
                duration=min(duration, self.current_clip.duration),
                position=position
            )
            
            # Composite with current video
            composite_clip = CompositeVideoClip([
                self.current_clip,
                text_overlay['clip']
            ])
            
            self.current_clip = composite_clip
            print(f"Added text overlay: '{text}' using template '{template_name}'")
            return True
            
        except Exception as e:
            print(f"Error adding text overlay: {e}")
            return False
    
    def create_title_sequence(self, titles: List[dict], background_color: Tuple[int, int, int] = (0, 0, 0)) -> bool:
        """Create a title sequence"""
        try:
            # Calculate total duration
            total_duration = max(title.get('start_time', 0) + title.get('duration', 3.0) for title in titles)
            
            # Create title sequence
            title_sequence = self.title_system.create_title_sequence(titles, total_duration)
            
            # If we have a current clip, composite with it
            if self.current_clip:
                # Ensure duration matches
                title_sequence = title_sequence.set_duration(min(total_duration, self.current_clip.duration))
                composite_clip = CompositeVideoClip([
                    self.current_clip,
                    title_sequence
                ])
                self.current_clip = composite_clip
            else:
                # Use title sequence as main clip
                self.current_clip = title_sequence
            
            print(f"Created title sequence with {len(titles)} titles")
            return True
            
        except Exception as e:
            print(f"Error creating title sequence: {e}")
            return False
    
    def get_available_text_templates(self) -> List[str]:
        """Get list of available text templates"""
        return self.title_system.list_templates()
    
    def save_text_templates(self, filepath: str) -> bool:
        """Save text templates to file"""
        try:
            self.title_system.save_templates(filepath)
            return True
        except Exception as e:
            print(f"Error saving templates: {e}")
            return False
    
    def load_text_templates(self, filepath: str) -> bool:
        """Load text templates from file"""
        try:
            self.title_system.load_templates(filepath)
            return True
        except Exception as e:
            print(f"Error loading templates: {e}")
            return False
    
    def get_export_presets(self) -> List[ExportPreset]:
        """Get all available export presets"""
        return self.export_presets_manager.get_all_presets()
    
    def get_preset_categories(self) -> List[str]:
        """Get all preset categories"""
        return self.export_presets_manager.get_categories()
    
    def get_presets_by_category(self, category: str) -> List[ExportPreset]:
        """Get presets in a specific category"""
        return self.export_presets_manager.get_presets_by_category(category)
    
    def create_custom_preset(self, name: str, description: str, **kwargs) -> ExportPreset:
        """Create a custom export preset"""
        return self.export_presets_manager.create_custom_preset(name, description, **kwargs)
    
    def get_preset_by_name(self, name: str) -> Optional[ExportPreset]:
        """Get a specific preset by name"""
        return self.export_presets_manager.get_preset(name)
    
    def estimate_export_file_size(self, preset_name: str) -> dict:
        """Estimate file size for export with given preset"""
        preset = self.export_presets_manager.get_preset(preset_name)
        if not preset:
            return {'error': 'Preset not found'}
            
        # Calculate total duration from timeline clips
        total_duration = 0
        if self.timeline_clips:
            sorted_clips = sorted(self.timeline_clips, key=lambda x: x['start_time'])
            if sorted_clips:
                last_clip = sorted_clips[-1]
                total_duration = last_clip['start_time'] + last_clip['duration']
        elif self.current_clip:
            total_duration = self.current_clip.duration
            
        return self.export_presets_manager.estimate_file_size(preset, total_duration)
    
    def export_video(self, output_path: str, codec: str = 'libx264', audio_bitrate: str = '256k', video_bitrate: str = '4000k') -> bool:
        """Export the final video (legacy method for backward compatibility)"""
        if not self.timeline_clips:
            print("No clips in timeline to export")
            return False
            
        try:
            # Sort clips by start time
            sorted_clips = sorted(self.timeline_clips, key=lambda x: x['start_time'])
            
            # Create composite video
            clips_for_export = [item['clip'] for item in sorted_clips]
            final_video = concatenate_videoclips(clips_for_export)
            
            # Export with progress callback
            final_video.write_videofile(
                output_path,
                codec=codec,
                audio_codec='aac',
                audio_bitrate=audio_bitrate,
                bitrate=video_bitrate,
                verbose=True,
                logger='bar'
            )
            
            print(f"Video exported to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting video: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        for clip in self.clips:
            clip.close()
        self.clips.clear()
        self.current_clip = None
        self.timeline_clips.clear()
