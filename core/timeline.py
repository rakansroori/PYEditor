"""
Timeline management for video editing
Handles multiple tracks, clips positioning, and timeline operations
"""

from typing import List, Dict, Optional, Tuple
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip
import uuid
from .keyframing import AnimationManager
from .performance_optimizer import auto_optimize

class TimelineClip:
    def __init__(self, clip, start_time: float = 0, track: int = 0):
        self.id = str(uuid.uuid4())
        self.clip = clip
        self.start_time = start_time
        self.track = track
        self.duration = clip.duration
        self.end_time = start_time + clip.duration
        self.selected = False
        self.animation = AnimationManager()  # Add keyframing support
        
    def move_to(self, new_start_time: float):
        """Move clip to new position"""
        self.start_time = new_start_time
        self.end_time = new_start_time + self.duration
        
    def trim(self, new_start: float, new_end: float):
        """Trim clip to new duration"""
        if new_start < 0 or new_end > self.clip.duration:
            raise ValueError("Trim bounds exceed clip duration")
            
        self.clip = self.clip.subclip(new_start, new_end)
        self.duration = new_end - new_start
        self.end_time = self.start_time + self.duration
    
    def add_keyframe(self, property_name: str, time: float, value, component: str = None):
        """Add keyframe for animation property"""
        # Convert global time to local clip time
        local_time = time - self.start_time
        if 0 <= local_time <= self.duration:
            self.animation.add_keyframe(property_name, local_time, value, component)
    
    def remove_keyframe(self, property_name: str, time: float, component: str = None):
        """Remove keyframe for animation property"""
        local_time = time - self.start_time
        self.animation.remove_keyframe(property_name, local_time, component)
    
    def evaluate_animation(self, time: float) -> Dict:
        """Evaluate all animation properties at given time"""
        local_time = time - self.start_time
        if 0 <= local_time <= self.duration:
            return self.animation.evaluate_all(local_time)
        return {}
    
    def apply_animation_to_clip(self, time: float):
        """Apply current animation state to the clip"""
        try:
            properties = self.evaluate_animation(time)
            
            # Apply transformations if keyframes exist
            animated_clip = self.clip
            
            # Position animation
            if self.animation.has_keyframes('position'):
                pos_x, pos_y = properties['position']
                animated_clip = animated_clip.with_position((pos_x, pos_y))
            
            # Scale animation
            if self.animation.has_keyframes('scale'):
                scale_x, scale_y = properties['scale']
                # MoviePy uses resize for scaling
                animated_clip = animated_clip.resize((scale_x, scale_y))
            
            # Rotation animation
            if self.animation.has_keyframes('rotation'):
                rotation = properties['rotation']
                animated_clip = animated_clip.rotate(rotation)
            
            # Opacity animation
            if self.animation.has_keyframes('opacity'):
                opacity = properties['opacity']
                # Apply opacity using fx
                animated_clip = animated_clip.set_opacity(opacity)
            
            return animated_clip
            
        except Exception as e:
            print(f"Error applying animation: {e}")
            return self.clip

class Track:
    """Represents a single track on the timeline"""
    def __init__(self, track_type: str = 'video'):
        self.clips: List[TimelineClip] = []
        self.locked = False
        self.muted = False
        self.solo = False
        self.name = f"{track_type.title()} Track"
        self.track_type = track_type
        self.height = 60  # Default track height in pixels
        self.color = '#4CAF50' if track_type == 'video' else '#2196F3'

class Timeline:
    def __init__(self):
        self.clips: List[TimelineClip] = []
        self.video_tracks: List[Track] = []
        self.audio_tracks: List[Track] = []
        self.current_time = 0.0
        self.zoom_level = 1.0
        self.selected_clips: List[str] = []
        self.snapping_enabled = True
        self.snap_threshold = 0.1  # Seconds
        self.ripple_mode = False
        self.magnetic_timeline = True
        
    def get_tracks(self, track_type: str) -> List[Track]:
        """Get tracks by type"""
        return self.video_tracks if track_type == 'video' else self.audio_tracks
        
    def ensure_track_exists(self, track_type: str, track_index: int):
        """Ensure track exists at given index"""
        tracks = self.get_tracks(track_type)
        while len(tracks) <= track_index:
            tracks.append(Track(track_type))
    
    def is_track_locked(self, track_type: str, track_index: int) -> bool:
        """Check if a track is locked"""
        tracks = self.get_tracks(track_type)
        if track_index < len(tracks):
            return tracks[track_index].locked
        return False

    def lock_track(self, track_type: str, track_index: int):
        """Lock a track"""
        self.ensure_track_exists(track_type, track_index)
        tracks = self.get_tracks(track_type)
        tracks[track_index].locked = True

    def unlock_track(self, track_type: str, track_index: int):
        """Unlock a track"""
        tracks = self.get_tracks(track_type)
        if track_index < len(tracks):
            tracks[track_index].locked = False
            
    def mute_track(self, track_type: str, track_index: int):
        """Mute a track"""
        tracks = self.get_tracks(track_type)
        if track_index < len(tracks):
            tracks[track_index].muted = True
            
    def unmute_track(self, track_type: str, track_index: int):
        """Unmute a track"""
        tracks = self.get_tracks(track_type)
        if track_index < len(tracks):
            tracks[track_index].muted = False
            
    def solo_track(self, track_type: str, track_index: int):
        """Solo a track (mute all others)"""
        tracks = self.get_tracks(track_type)
        for i, track in enumerate(tracks):
            track.solo = (i == track_index)

    def enable_snapping(self, enable: bool):
        """Enable or disable snapping behavior"""
        self.snapping_enabled = enable
        
    def enable_ripple_mode(self, enable: bool):
        """Enable or disable ripple editing"""
        self.ripple_mode = enable
        
    def enable_magnetic_timeline(self, enable: bool):
        """Enable or disable magnetic timeline"""
        self.magnetic_timeline = enable

    def get_snap_positions(self) -> List[float]:
        """Get all possible snap positions"""
        positions = [0.0]  # Timeline start
        for clip in self.clips:
            positions.extend([clip.start_time, clip.end_time])
        return sorted(set(positions))

    def get_nearest_snap_position(self, time: float) -> float:
        """Find nearest snap position"""
        if not self.snapping_enabled:
            return time
            
        snap_positions = self.get_snap_positions()
        if not snap_positions:
            return time
            
        closest_snap = min(snap_positions, key=lambda snap_time: abs(snap_time - time))
        if abs(closest_snap - time) <= self.snap_threshold:
            return closest_snap
        return time
        
    def find_gaps(self, track_type: str, track_index: int) -> List[Tuple[float, float]]:
        """Find gaps in a track where clips can be inserted"""
        tracks = self.get_tracks(track_type)
        if track_index >= len(tracks):
            return [(0.0, float('inf'))]
            
        track = tracks[track_index]
        if not track.clips:
            return [(0.0, float('inf'))]
            
        # Sort clips by start time
        sorted_clips = sorted(track.clips, key=lambda c: c.start_time)
        gaps = []
        
        # Gap before first clip
        if sorted_clips[0].start_time > 0:
            gaps.append((0.0, sorted_clips[0].start_time))
            
        # Gaps between clips
        for i in range(len(sorted_clips) - 1):
            gap_start = sorted_clips[i].end_time
            gap_end = sorted_clips[i + 1].start_time
            if gap_end > gap_start:
                gaps.append((gap_start, gap_end))
                
        # Gap after last clip
        gaps.append((sorted_clips[-1].end_time, float('inf')))
        
        return gaps

    def add_clip(self, clip, start_time: float = 0, track: int = 0) -> str:
        """Add clip to timeline"""
        # Determine track type
        track_type = 'video' if hasattr(clip, 'fps') else 'audio'
        
        # Check if track is locked
        if self.is_track_locked(track_type, track):
            raise ValueError(f"Track {track} is locked. Cannot add clip.")
            
        # Ensure track exists
        self.ensure_track_exists(track_type, track)
        
        # Apply snapping if enabled
        if self.snapping_enabled:
            start_time = self.get_nearest_snap_position(start_time)
            
        # Create timeline clip
        timeline_clip = TimelineClip(clip, start_time, track)
        self.clips.append(timeline_clip)
        
        # Add to appropriate track
        tracks = self.get_tracks(track_type)
        tracks[track].clips.append(timeline_clip)
        
        return timeline_clip.id
        
    def remove_clip(self, clip_id: str) -> bool:
        """Remove clip from timeline"""
        clip_to_remove = None
        for clip in self.clips:
            if clip.id == clip_id:
                clip_to_remove = clip
                break
                
        if not clip_to_remove:
            return False
            
        # Remove from clips list
        self.clips.remove(clip_to_remove)
        
        # Remove from tracks
        track_type = 'video' if hasattr(clip_to_remove.clip, 'fps') else 'audio'
        if clip_to_remove.track < len(self.tracks[track_type]):
            self.tracks[track_type][clip_to_remove.track].remove(clip_to_remove)
            
        # Remove from selection
        if clip_id in self.selected_clips:
            self.selected_clips.remove(clip_id)
            
        return True
        
    def move_clip(self, clip_id: str, new_start_time: float, new_track: int = None, magnetic: bool = True) -> bool:
        """Move clip to new position"""
        clip = self.get_clip_by_id(clip_id)
        if not clip:
            return False
            
        old_track = clip.track
        track_type = 'video' if hasattr(clip.clip, 'fps') else 'audio'
        
        # Remove from old track
        if old_track < len(self.tracks[track_type]):
            self.tracks[track_type][old_track].remove(clip)
            
        # Update clip position
        # Snap to nearest position if magnetic timeline is enabled
        if magnetic and self.magnetic_timeline:
            new_start_time = self.get_nearest_snap_position(new_start_time)
        if self.snapping_enabled:
            new_start_time = self.get_nearest_snap_position(new_start_time)

        clip.move_to(new_start_time)
        
        # Update track if specified
        if new_track is not None:
            clip.track = new_track
            
            # Ensure new track exists
            if new_track >= len(self.tracks[track_type]):
                for i in range(len(self.tracks[track_type]), new_track + 1):
                    self.tracks[track_type].append([])
                    
            self.tracks[track_type][new_track].append(clip)
        else:
            # Add back to same track
            self.tracks[track_type][old_track].append(clip)
            
        return True
        
    def get_clip_by_id(self, clip_id: str) -> Optional[TimelineClip]:
        """Get clip by ID"""
        for clip in self.clips:
            if clip.id == clip_id:
                return clip
        return None
        
    def get_clips_at_time(self, time: float) -> List[TimelineClip]:
        """Get all clips active at given time"""
        active_clips = []
        for clip in self.clips:
            if clip.start_time <= time <= clip.end_time:
                active_clips.append(clip)
        return active_clips
        
    def get_clips_in_range(self, start_time: float, end_time: float) -> List[TimelineClip]:
        """Get clips within time range"""
        clips_in_range = []
        for clip in self.clips:
            # Check if clip overlaps with range
            if (clip.start_time < end_time and clip.end_time > start_time):
                clips_in_range.append(clip)
        return clips_in_range
        
    def select_clip(self, clip_id: str):
        """Select a clip"""
        if clip_id not in self.selected_clips:
            self.selected_clips.append(clip_id)
            clip = self.get_clip_by_id(clip_id)
            if clip:
                clip.selected = True
                
    def deselect_clip(self, clip_id: str):
        """Deselect a clip"""
        if clip_id in self.selected_clips:
            self.selected_clips.remove(clip_id)
            clip = self.get_clip_by_id(clip_id)
            if clip:
                clip.selected = False
                
    def clear_selection(self):
        """Clear all selections"""
        for clip_id in self.selected_clips:
            clip = self.get_clip_by_id(clip_id)
            if clip:
                clip.selected = False
        self.selected_clips.clear()
        
    def get_total_duration(self) -> float:
        """Get total timeline duration"""
        if not self.clips:
            return 0.0
        return max(clip.end_time for clip in self.clips)
        
    def duplicate_clip(self, clip_id: str) -> Optional[str]:
        """Duplicate a clip"""
        original_clip = self.get_clip_by_id(clip_id)
        if not original_clip:
            return None
            
        # Create new clip at end of original
        new_start_time = original_clip.end_time
        return self.add_clip(original_clip.clip, new_start_time, original_clip.track)
        
    def split_clip(self, clip_id: str, split_time: float) -> Tuple[Optional[str], Optional[str]]:
        """Split clip at given time"""
        clip = self.get_clip_by_id(clip_id)
        if not clip:
            return None, None
            
        # Check if split time is valid
        relative_split_time = split_time - clip.start_time
        if relative_split_time <= 0 or relative_split_time >= clip.duration:
            return None, None
            
        try:
            # Create two new clips
            first_part = clip.clip.subclip(0, relative_split_time)
            second_part = clip.clip.subclip(relative_split_time, clip.duration)
            
            # Remove original clip
            track = clip.track
            self.remove_clip(clip_id)
            
            # Add new clips
            first_id = self.add_clip(first_part, clip.start_time, track)
            second_id = self.add_clip(second_part, split_time, track)
            
            return first_id, second_id
            
        except Exception as e:
            print(f"Error splitting clip: {e}")
            return None, None
    
    def add_keyframe_to_clip(self, clip_id: str, property_name: str, time: float, value, component: str = None):
        """Add keyframe to specific clip"""
        clip = self.get_clip_by_id(clip_id)
        if clip:
            clip.add_keyframe(property_name, time, value, component)
            return True
        return False
    
    def remove_keyframe_from_clip(self, clip_id: str, property_name: str, time: float, component: str = None):
        """Remove keyframe from specific clip"""
        clip = self.get_clip_by_id(clip_id)
        if clip:
            clip.remove_keyframe(property_name, time, component)
            return True
        return False
    
    def get_animated_clips_at_time(self, time: float) -> List[TimelineClip]:
        """Get all clips with animations active at given time"""
        active_clips = self.get_clips_at_time(time)
        return [clip for clip in active_clips if clip.animation.has_keyframes()]
    
    def render_frame_at_time(self, time: float):
        """Render a frame with all animations applied at given time"""
        try:
            # Get all active clips
            active_clips = self.get_clips_at_time(time)
            
            if not active_clips:
                return None
                
            # Apply animations to clips
            animated_clips = []
            for clip in active_clips:
                if clip.animation.has_keyframes():
                    animated_clip = clip.apply_animation_to_clip(time)
                    animated_clips.append(animated_clip)
                else:
                    animated_clips.append(clip.clip)
            
            # If multiple clips, composite them
            if len(animated_clips) == 1:
                return animated_clips[0]
            else:
                # Create composite of all clips
                from moviepy.editor import CompositeVideoClip
                return CompositeVideoClip(animated_clips)
                
        except Exception as e:
            print(f"Error rendering frame: {e}")
            return None
    
    @auto_optimize('video_export')
    def export_video(self, file_path: str):
        """Example method to export video using optimization"""
        print(f"Exporting video to {file_path} with optimizations...")
        # Placeholder for actual export logic
        pass
    
    def enable_multicam_editing(self):
        """Enable multi-camera editing capabilities for this timeline"""
        try:
            from .multicam_editor import extend_timeline_with_multicam
            return extend_timeline_with_multicam(self)
        except ImportError:
            print("Multi-camera editing module not available")
            return None
    
    def is_multicam_compatible(self) -> bool:
        """Check if timeline is compatible with multi-camera editing"""
        try:
            from .multicam_editor import MultiCamTimeline
            return True
        except ImportError:
            return False
