"""
Multi-camera editing system for PyVideoEditor
Handles synchronization, angle switching, and multi-cam timeline management
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import uuid
import threading
import time
from datetime import datetime, timedelta

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
    from moviepy.audio.fx import volumex
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip

from .timeline import Timeline, TimelineClip

class SyncMethod(Enum):
    """Methods for synchronizing multi-camera footage"""
    AUDIO_WAVEFORM = "audio_waveform"
    TIMECODE = "timecode"
    MANUAL = "manual"
    CLAP_DETECTION = "clap_detection"
    FLASH_SYNC = "flash_sync"

class CameraAngle(Enum):
    """Standard camera angle definitions"""
    WIDE_SHOT = "wide_shot"
    MEDIUM_SHOT = "medium_shot"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_SHOULDER = "over_shoulder"
    PROFILE = "profile"
    CUSTOM = "custom"

@dataclass
class CameraClip:
    """Represents a single camera's footage in a multi-cam setup"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clip_path: str = ""
    camera_name: str = ""
    angle: CameraAngle = CameraAngle.WIDE_SHOT
    clip: Optional[Any] = None
    timecode_start: Optional[datetime] = None
    sync_offset: float = 0.0  # Offset in seconds from master timeline
    audio_enabled: bool = True
    video_enabled: bool = True
    color_correction: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.clip is None and self.clip_path:
            try:
                self.clip = VideoFileClip(self.clip_path)
            except Exception as e:
                print(f"Error loading clip {self.clip_path}: {e}")

@dataclass
class MultiCamSequence:
    """A sequence of synchronized camera clips"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Multi-Cam Sequence"
    cameras: List[CameraClip] = field(default_factory=list)
    master_camera: Optional[str] = None  # ID of master camera for sync
    sync_method: SyncMethod = SyncMethod.AUDIO_WAVEFORM
    sequence_start: float = 0.0
    sequence_duration: Optional[float] = None
    auto_sync_enabled: bool = True
    sync_tolerance: float = 0.1  # Seconds
    created_at: datetime = field(default_factory=datetime.now)

class AudioAnalyzer:
    """Utility class for audio-based synchronization"""
    
    @staticmethod
    def extract_audio_features(clip) -> np.ndarray:
        """Extract audio features for sync analysis"""
        try:
            if hasattr(clip, 'audio') and clip.audio is not None:
                # Get audio array
                audio = clip.audio.to_soundarray(fps=22050)
                if len(audio.shape) > 1:
                    # Convert stereo to mono
                    audio = np.mean(audio, axis=1)
                
                # Compute RMS energy in windows
                window_size = 1024
                hop_size = 512
                rms_values = []
                
                for i in range(0, len(audio) - window_size, hop_size):
                    window = audio[i:i + window_size]
                    rms = np.sqrt(np.mean(window ** 2))
                    rms_values.append(rms)
                
                return np.array(rms_values)
            return np.array([])
        except Exception as e:
            print(f"Error extracting audio features: {e}")
            return np.array([])
    
    @staticmethod
    def find_sync_offset(master_features: np.ndarray, slave_features: np.ndarray) -> float:
        """Find sync offset between two audio tracks using cross-correlation"""
        try:
            if len(master_features) == 0 or len(slave_features) == 0:
                return 0.0
            
            # Normalize features
            master_norm = (master_features - np.mean(master_features)) / (np.std(master_features) + 1e-8)
            slave_norm = (slave_features - np.mean(slave_features)) / (np.std(slave_features) + 1e-8)
            
            # Cross-correlation
            correlation = np.correlate(master_norm, slave_norm, mode='full')
            
            # Find peak
            peak_index = np.argmax(correlation)
            offset_samples = peak_index - (len(slave_norm) - 1)
            
            # Convert to seconds (assuming 22050 Hz with hop size 512)
            hop_duration = 512.0 / 22050.0
            offset_seconds = offset_samples * hop_duration
            
            return offset_seconds
            
        except Exception as e:
            print(f"Error finding sync offset: {e}")
            return 0.0

class MultiCamSyncEngine:
    """Engine for synchronizing multiple camera clips"""
    
    def __init__(self):
        self.audio_analyzer = AudioAnalyzer()
        
    def sync_by_audio(self, sequence: MultiCamSequence) -> bool:
        """Synchronize cameras using audio waveform analysis"""
        try:
            if not sequence.cameras or len(sequence.cameras) < 2:
                return False
                
            # Find master camera
            master_camera = self._get_master_camera(sequence)
            if not master_camera or not master_camera.clip:
                return False
                
            # Extract master audio features
            master_features = self.audio_analyzer.extract_audio_features(master_camera.clip)
            if len(master_features) == 0:
                print("Warning: Master camera has no audio for sync")
                return False
            
            # Sync each slave camera
            for camera in sequence.cameras:
                if camera.id == master_camera.id:
                    camera.sync_offset = 0.0
                    continue
                    
                if not camera.clip:
                    continue
                    
                # Extract slave audio features
                slave_features = self.audio_analyzer.extract_audio_features(camera.clip)
                if len(slave_features) == 0:
                    print(f"Warning: Camera {camera.camera_name} has no audio for sync")
                    continue
                
                # Calculate sync offset
                offset = self.audio_analyzer.find_sync_offset(master_features, slave_features)
                camera.sync_offset = offset
                
                print(f"Synced {camera.camera_name}: offset = {offset:.3f}s")
                
            return True
            
        except Exception as e:
            print(f"Error in audio sync: {e}")
            return False
    
    def sync_by_timecode(self, sequence: MultiCamSequence) -> bool:
        """Synchronize cameras using embedded timecode"""
        try:
            if not sequence.cameras:
                return False
                
            # Find earliest timecode as reference
            reference_time = None
            for camera in sequence.cameras:
                if camera.timecode_start:
                    if reference_time is None or camera.timecode_start < reference_time:
                        reference_time = camera.timecode_start
            
            if reference_time is None:
                print("No timecode information available")
                return False
                
            # Calculate offsets based on timecode differences
            for camera in sequence.cameras:
                if camera.timecode_start:
                    time_diff = camera.timecode_start - reference_time
                    camera.sync_offset = time_diff.total_seconds()
                else:
                    camera.sync_offset = 0.0
                    
            return True
            
        except Exception as e:
            print(f"Error in timecode sync: {e}")
            return False
    
    def sync_by_clap_detection(self, sequence: MultiCamSequence) -> bool:
        """Synchronize using clap/slate detection"""
        try:
            # This would implement clap detection algorithm
            # For now, return basic implementation
            print("Clap detection sync not yet implemented")
            return False
            
        except Exception as e:
            print(f"Error in clap detection sync: {e}")
            return False
    
    def _get_master_camera(self, sequence: MultiCamSequence) -> Optional[CameraClip]:
        """Get the master camera for synchronization"""
        if sequence.master_camera:
            for camera in sequence.cameras:
                if camera.id == sequence.master_camera:
                    return camera
        
        # Default to first camera with audio
        for camera in sequence.cameras:
            if camera.clip and hasattr(camera.clip, 'audio') and camera.clip.audio:
                return camera
                
        # Fallback to first camera
        return sequence.cameras[0] if sequence.cameras else None

class MultiCamTimeline:
    """Extended timeline for multi-camera editing"""
    
    def __init__(self, base_timeline: Timeline):
        self.base_timeline = base_timeline
        self.multicam_sequences: List[MultiCamSequence] = []
        self.active_sequence: Optional[str] = None
        self.current_angles: Dict[str, str] = {}  # sequence_id -> camera_id
        self.sync_engine = MultiCamSyncEngine()
        
    def create_multicam_sequence(self, 
                                name: str,
                                camera_clips: List[Tuple[str, str, CameraAngle]],  # (path, name, angle)
                                sync_method: SyncMethod = SyncMethod.AUDIO_WAVEFORM) -> str:
        """Create a new multi-camera sequence"""
        
        # Create camera clips
        cameras = []
        for clip_path, camera_name, angle in camera_clips:
            camera = CameraClip(
                clip_path=clip_path,
                camera_name=camera_name,
                angle=angle
            )
            cameras.append(camera)
        
        # Create sequence
        sequence = MultiCamSequence(
            name=name,
            cameras=cameras,
            sync_method=sync_method
        )
        
        # Auto-sync if enabled
        if sequence.auto_sync_enabled:
            self.sync_sequence(sequence.id)
        
        self.multicam_sequences.append(sequence)
        
        # Set as active sequence if it's the first one
        if not self.active_sequence:
            self.active_sequence = sequence.id
            
        return sequence.id
    
    def sync_sequence(self, sequence_id: str) -> bool:
        """Synchronize a multi-camera sequence"""
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False
            
        if sequence.sync_method == SyncMethod.AUDIO_WAVEFORM:
            return self.sync_engine.sync_by_audio(sequence)
        elif sequence.sync_method == SyncMethod.TIMECODE:
            return self.sync_engine.sync_by_timecode(sequence)
        elif sequence.sync_method == SyncMethod.CLAP_DETECTION:
            return self.sync_engine.sync_by_clap_detection(sequence)
        else:
            print(f"Sync method {sequence.sync_method} not implemented")
            return False
    
    def add_multicam_to_timeline(self, sequence_id: str, start_time: float = 0.0, track: int = 0) -> str:
        """Add multi-camera sequence to timeline"""
        sequence = self.get_sequence(sequence_id)
        if not sequence or not sequence.cameras:
            return ""
            
        # Create a multicam clip (initially using first camera)
        master_camera = sequence.cameras[0]
        if not master_camera.clip:
            return ""
            
        # Add to timeline
        clip_id = self.base_timeline.add_clip(master_camera.clip, start_time, track)
        
        # Set current angle
        self.current_angles[sequence_id] = master_camera.id
        
        return clip_id
    
    def switch_angle(self, sequence_id: str, camera_id: str, timeline_clip_id: str) -> bool:
        """Switch to a different camera angle"""
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False
            
        # Find the camera
        target_camera = None
        for camera in sequence.cameras:
            if camera.id == camera_id:
                target_camera = camera
                break
                
        if not target_camera or not target_camera.clip:
            return False
            
        # Get the timeline clip
        timeline_clip = self.base_timeline.get_clip_by_id(timeline_clip_id)
        if not timeline_clip:
            return False
            
        # Apply sync offset to the new camera
        synced_clip = target_camera.clip
        if target_camera.sync_offset != 0:
            # Adjust clip timing based on sync offset
            start_offset = max(0, -target_camera.sync_offset)
            end_offset = target_camera.clip.duration + min(0, -target_camera.sync_offset)
            if start_offset < end_offset:
                synced_clip = target_camera.clip.subclip(start_offset, end_offset)
        
        # Replace the clip in timeline
        timeline_clip.clip = synced_clip
        timeline_clip.duration = synced_clip.duration
        timeline_clip.end_time = timeline_clip.start_time + timeline_clip.duration
        
        # Update current angle
        self.current_angles[sequence_id] = camera_id
        
        return True
    
    def create_multicam_cut(self, sequence_id: str, cuts: List[Tuple[float, str]]) -> bool:
        """Create automatic cuts between camera angles
        
        Args:
            sequence_id: ID of the multicam sequence
            cuts: List of (time, camera_id) tuples defining when to cut to which camera
        """
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False
            
        # Sort cuts by time
        cuts.sort(key=lambda x: x[0])
        
        # Create clips for each segment
        for i, (cut_time, camera_id) in enumerate(cuts):
            # Find the camera
            camera = None
            for cam in sequence.cameras:
                if cam.id == camera_id:
                    camera = cam
                    break
                    
            if not camera or not camera.clip:
                continue
                
            # Calculate segment duration
            if i < len(cuts) - 1:
                segment_duration = cuts[i + 1][0] - cut_time
            else:
                segment_duration = camera.clip.duration - cut_time
                
            if segment_duration <= 0:
                continue
                
            # Create subclip with sync offset
            start_in_source = cut_time + camera.sync_offset
            end_in_source = start_in_source + segment_duration
            
            if start_in_source >= 0 and end_in_source <= camera.clip.duration:
                segment_clip = camera.clip.subclip(start_in_source, end_in_source)
                
                # Add to timeline
                track = i % 4  # Distribute across 4 tracks
                self.base_timeline.add_clip(segment_clip, cut_time, track)
        
        return True
    
    def get_sequence(self, sequence_id: str) -> Optional[MultiCamSequence]:
        """Get multicam sequence by ID"""
        for sequence in self.multicam_sequences:
            if sequence.id == sequence_id:
                return sequence
        return None
    
    def get_cameras_in_sequence(self, sequence_id: str) -> List[CameraClip]:
        """Get all cameras in a sequence"""
        sequence = self.get_sequence(sequence_id)
        return sequence.cameras if sequence else []
    
    def set_camera_audio_enabled(self, sequence_id: str, camera_id: str, enabled: bool) -> bool:
        """Enable/disable audio for a specific camera"""
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False
            
        for camera in sequence.cameras:
            if camera.id == camera_id:
                camera.audio_enabled = enabled
                return True
        return False
    
    def adjust_camera_sync(self, sequence_id: str, camera_id: str, offset_adjustment: float) -> bool:
        """Manually adjust sync offset for a camera"""
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False
            
        for camera in sequence.cameras:
            if camera.id == camera_id:
                camera.sync_offset += offset_adjustment
                return True
        return False

class MultiCamEffects:
    """Special effects for multi-camera editing"""
    
    @staticmethod
    def create_picture_in_picture(main_clip, pip_clip, position=(0.7, 0.1), size=0.3):
        """Create picture-in-picture effect with two camera angles"""
        try:
            # Resize the PiP clip
            pip_resized = pip_clip.resize(size)
            
            # Position the PiP clip  
            pip_positioned = pip_resized.set_position(position)
            
            # Composite the clips
            return CompositeVideoClip([main_clip, pip_positioned])
            
        except Exception as e:
            print(f"Error creating picture-in-picture: {e}")
            return main_clip
    
    @staticmethod
    def create_split_screen(clips: List, layout='horizontal'):
        """Create split screen with multiple camera angles"""
        try:
            if not clips:
                return None
                
            if len(clips) == 1:
                return clips[0]
                
            if layout == 'horizontal':
                # Resize each clip to fit horizontally
                width_ratio = 1.0 / len(clips)
                positioned_clips = []
                
                for i, clip in enumerate(clips):
                    resized = clip.resize(width=width_ratio)
                    positioned = resized.set_position((i * width_ratio, 0))
                    positioned_clips.append(positioned)
                    
            elif layout == 'vertical':
                # Resize each clip to fit vertically
                height_ratio = 1.0 / len(clips)
                positioned_clips = []
                
                for i, clip in enumerate(clips):
                    resized = clip.resize(height=height_ratio)
                    positioned = resized.set_position((0, i * height_ratio))
                    positioned_clips.append(positioned)
                    
            elif layout == 'grid':  
                # Arrange in grid
                import math
                grid_size = math.ceil(math.sqrt(len(clips)))
                cell_width = 1.0 / grid_size
                cell_height = 1.0 / grid_size
                
                positioned_clips = []
                for i, clip in enumerate(clips):
                    row = i // grid_size
                    col = i % grid_size
                    
                    resized = clip.resize(width=cell_width, height=cell_height)
                    positioned = resized.set_position((col * cell_width, row * cell_height))
                    positioned_clips.append(positioned)
            
            return CompositeVideoClip(positioned_clips)
            
        except Exception as e:
            print(f"Error creating split screen: {e}")
            return clips[0] if clips else None

class MulticamEditor:
    """Main multi-camera editor class that orchestrates all multicam functionality"""
    
    def __init__(self):
        self.timeline = None
        self.multicam_timeline = None
        self.sync_engine = MultiCamSyncEngine()
        self.effects = MultiCamEffects()
        
    def set_timeline(self, timeline: Timeline):
        """Set the base timeline for multicam editing"""
        self.timeline = timeline
        self.multicam_timeline = MultiCamTimeline(timeline)
        
    def create_sequence(self, name: str, camera_clips: List[Tuple[str, str, CameraAngle]], 
                      sync_method: SyncMethod = SyncMethod.AUDIO_WAVEFORM) -> str:
        """Create a new multicam sequence"""
        if not self.multicam_timeline:
            raise ValueError("Timeline not set. Call set_timeline() first.")
        return self.multicam_timeline.create_multicam_sequence(name, camera_clips, sync_method)
        
    def sync_sequence(self, sequence_id: str) -> bool:
        """Sync a multicam sequence"""
        if not self.multicam_timeline:
            return False
        return self.multicam_timeline.sync_sequence(sequence_id)
        
    def switch_angle(self, sequence_id: str, camera_id: str, timeline_clip_id: str) -> bool:
        """Switch camera angle"""
        if not self.multicam_timeline:
            return False
        return self.multicam_timeline.switch_angle(sequence_id, camera_id, timeline_clip_id)
        
    def create_picture_in_picture(self, main_clip, pip_clip, position=(0.7, 0.1), size=0.3):
        """Create picture-in-picture effect"""
        return self.effects.create_picture_in_picture(main_clip, pip_clip, position, size)
        
    def create_split_screen(self, clips: List, layout='horizontal'):
        """Create split screen effect"""
        return self.effects.create_split_screen(clips, layout)

# Integration with existing timeline
def extend_timeline_with_multicam(timeline: Timeline) -> MultiCamTimeline:
    """Extend an existing timeline with multi-camera capabilities"""
    return MultiCamTimeline(timeline)
