"""
Advanced Nested Timeline System for PyVideoEditor
Enables complex editing workflows with timelines within timelines
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import copy
from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips
from .timeline import Timeline, TimelineClip as BaseTimelineClip
from .keyframing import AnimationManager

class TimelineType(Enum):
    """Types of timelines"""
    MAIN = "main"
    NESTED = "nested"
    COMPOUND = "compound"
    ADJUSTMENT = "adjustment"

@dataclass
class NestedTimelineMetadata:
    """Metadata for nested timelines"""
    timeline_id: str
    name: str
    description: str = ""
    created_by: str = ""
    creation_time: float = 0.0
    last_modified: float = 0.0
    tags: List[str] = field(default_factory=list)
    color: str = "#4A90E2"
    locked: bool = False

class NestedTimelineClip(BaseTimelineClip):
    """Enhanced timeline clip that can contain nested timelines"""
    
    def __init__(self, clip_id: str, name: str, start_time: float, 
                 duration: float, track: int, clip_type: str = "video"):
        super().__init__(clip_id, name, start_time, duration, track)
        self.clip_type = clip_type
        self.nested_timeline_id: Optional[str] = None
        self.is_nested = False
        self.nested_scale = 1.0
        self.nested_offset = 0.0
        self.render_cache = {}
        self.metadata = {}
        
    def set_nested_timeline(self, timeline_id: str):
        """Convert this clip to reference a nested timeline"""
        self.nested_timeline_id = timeline_id
        self.is_nested = True
        
    def clear_nested_timeline(self):
        """Remove nested timeline reference"""
        self.nested_timeline_id = None
        self.is_nested = False
        self.render_cache.clear()

class NestedTimeline(Timeline):
    """Enhanced timeline with nested timeline support"""
    
    def __init__(self, timeline_id: str = None, timeline_type: TimelineType = TimelineType.MAIN):
        super().__init__()
        self.timeline_id = timeline_id or str(uuid.uuid4())
        self.timeline_type = timeline_type
        self.metadata = NestedTimelineMetadata(
            timeline_id=self.timeline_id,
            name=f"Timeline {self.timeline_id[:8]}"
        )
        self.parent_timeline_id: Optional[str] = None
        self.child_timelines: Dict[str, 'NestedTimeline'] = {}
        self.render_settings = {
            'resolution': (1920, 1080),
            'fps': 30,
            'audio_sample_rate': 44100
        }
        
    def create_nested_timeline(self, name: str, timeline_type: TimelineType = TimelineType.NESTED) -> str:
        """Create a new nested timeline"""
        nested_id = str(uuid.uuid4())
        nested_timeline = NestedTimeline(nested_id, timeline_type)
        nested_timeline.metadata.name = name
        nested_timeline.parent_timeline_id = self.timeline_id
        
        self.child_timelines[nested_id] = nested_timeline
        return nested_id
        
    def get_nested_timeline(self, timeline_id: str) -> Optional['NestedTimeline']:
        """Get a nested timeline by ID"""
        return self.child_timelines.get(timeline_id)
        
    def delete_nested_timeline(self, timeline_id: str) -> bool:
        """Delete a nested timeline and update references"""
        if timeline_id not in self.child_timelines:
            return False
            
        # Remove references from clips
        for track in self.tracks.values():
            for clip in track.clips:
                if isinstance(clip, NestedTimelineClip) and clip.nested_timeline_id == timeline_id:
                    clip.clear_nested_timeline()
        
        # Remove the timeline
        del self.child_timelines[timeline_id]
        return True
        
    def convert_clips_to_nested(self, clip_ids: List[str], nested_name: str) -> Optional[str]:
        """Convert selected clips into a nested timeline"""
        if not clip_ids:
            return None
            
        # Create new nested timeline
        nested_id = self.create_nested_timeline(nested_name)
        nested_timeline = self.child_timelines[nested_id]
        
        clips_to_convert = []
        min_start_time = float('inf')
        
        # Find clips and calculate bounds
        for track in self.tracks.values():
            for clip in track.clips:
                if clip.clip_id in clip_ids:
                    clips_to_convert.append(clip)
                    min_start_time = min(min_start_time, clip.start_time)
        
        if not clips_to_convert:
            self.delete_nested_timeline(nested_id)
            return None
            
        # Move clips to nested timeline (adjust timing)
        for clip in clips_to_convert:
            # Create new clip in nested timeline
            nested_clip = NestedTimelineClip(
                clip.clip_id,
                clip.name,
                clip.start_time - min_start_time,  # Adjust to start from 0
                clip.duration,
                clip.track,
                getattr(clip, 'clip_type', 'video')
            )
            
            # Copy clip data
            if hasattr(clip, 'clip'):
                nested_clip.clip = clip.clip
            if hasattr(clip, 'animation'):
                nested_clip.animation = copy.deepcopy(clip.animation)
                
            # Add to nested timeline
            nested_timeline.add_clip_to_track(nested_clip, clip.track)
            
            # Remove from main timeline
            self.remove_clip_from_track(clip.clip_id, clip.track)
        
        # Create compound clip in main timeline
        compound_clip = NestedTimelineClip(
            f"compound_{nested_id[:8]}",
            nested_name,
            min_start_time,
            max(clip.start_time + clip.duration for clip in clips_to_convert) - min_start_time,
            clips_to_convert[0].track,
            "compound"
        )
        compound_clip.set_nested_timeline(nested_id)
        
        # Add compound clip to main timeline
        self.add_clip_to_track(compound_clip, compound_clip.track)
        
        return nested_id
        
    def flatten_nested_timeline(self, timeline_id: str) -> bool:
        """Flatten a nested timeline back to the main timeline"""
        nested_timeline = self.get_nested_timeline(timeline_id)
        if not nested_timeline:
            return False
            
        # Find the compound clip
        compound_clip = None
        compound_track = None
        
        for track_id, track in self.tracks.items():
            for clip in track.clips:
                if isinstance(clip, NestedTimelineClip) and clip.nested_timeline_id == timeline_id:
                    compound_clip = clip
                    compound_track = track_id
                    break
            if compound_clip:
                break
                
        if not compound_clip:
            return False
            
        # Move clips from nested timeline back to main timeline
        for track in nested_timeline.tracks.values():
            for nested_clip in track.clips:
                # Adjust timing back to main timeline
                flattened_clip = NestedTimelineClip(
                    f"flattened_{nested_clip.clip_id}",
                    nested_clip.name,
                    nested_clip.start_time + compound_clip.start_time,
                    nested_clip.duration,
                    nested_clip.track,
                    getattr(nested_clip, 'clip_type', 'video')
                )
                
                # Copy clip data
                if hasattr(nested_clip, 'clip'):
                    flattened_clip.clip = nested_clip.clip
                if hasattr(nested_clip, 'animation'):
                    flattened_clip.animation = copy.deepcopy(nested_clip.animation)
                    
                self.add_clip_to_track(flattened_clip, nested_clip.track)
        
        # Remove compound clip and nested timeline
        self.remove_clip_from_track(compound_clip.clip_id, compound_track)
        self.delete_nested_timeline(timeline_id)
        
        return True
        
    def render_nested_timeline(self, timeline_id: str, start_time: float, end_time: float) -> Optional[VideoFileClip]:
        """Render a nested timeline to a video clip"""
        nested_timeline = self.get_nested_timeline(timeline_id)
        if not nested_timeline:
            return None
            
        try:
            # Check cache first
            cache_key = f"{timeline_id}_{start_time}_{end_time}"
            if cache_key in nested_timeline.render_cache:
                return nested_timeline.render_cache[cache_key]
                
            # Collect all clips in time range
            clips_to_composite = []
            
            for track in nested_timeline.tracks.values():
                for clip in track.clips:
                    clip_start = clip.start_time
                    clip_end = clip.start_time + clip.duration
                    
                    # Check if clip overlaps with requested time range
                    if clip_start < end_time and clip_end > start_time:
                        if hasattr(clip, 'clip') and clip.clip:
                            # Calculate relative timing
                            relative_start = max(0, start_time - clip_start)
                            relative_end = min(clip.duration, end_time - clip_start)
                            
                            if relative_end > relative_start:
                                # Extract the relevant portion
                                clip_portion = clip.clip.subclip(relative_start, relative_end)
                                
                                # Apply positioning
                                clip_portion = clip_portion.with_start(clip_start - start_time)
                                
                                # Apply animations if present
                                if hasattr(clip, 'animation') and clip.animation:
                                    # Apply keyframe animations
                                    animated_clip = nested_timeline.apply_animation_to_clip_at_time(
                                        clip_portion, clip.animation, start_time
                                    )
                                    clips_to_composite.append(animated_clip)
                                else:
                                    clips_to_composite.append(clip_portion)
            
            if not clips_to_composite:
                return None
                
            # Create composite
            if len(clips_to_composite) == 1:
                result = clips_to_composite[0]
            else:
                result = CompositeVideoClip(clips_to_composite)
                
            # Cache the result
            nested_timeline.render_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"Error rendering nested timeline {timeline_id}: {e}")
            return None
            
    def get_timeline_hierarchy(self) -> Dict[str, Any]:
        """Get the complete timeline hierarchy"""
        hierarchy = {
            'timeline_id': self.timeline_id,
            'name': self.metadata.name,
            'type': self.timeline_type.value,
            'parent': self.parent_timeline_id,
            'children': {}
        }
        
        for child_id, child_timeline in self.child_timelines.items():
            hierarchy['children'][child_id] = child_timeline.get_timeline_hierarchy()
            
        return hierarchy
        
    def find_timeline_by_id(self, timeline_id: str) -> Optional['NestedTimeline']:
        """Find a timeline by ID in the hierarchy"""
        if self.timeline_id == timeline_id:
            return self
            
        for child_timeline in self.child_timelines.values():
            result = child_timeline.find_timeline_by_id(timeline_id)
            if result:
                return result
                
        return None
        
    def get_all_nested_clips(self) -> List[NestedTimelineClip]:
        """Get all clips that reference nested timelines"""
        nested_clips = []
        
        for track in self.tracks.values():
            for clip in track.clips:
                if isinstance(clip, NestedTimelineClip) and clip.is_nested:
                    nested_clips.append(clip)
                    
        return nested_clips
        
    def validate_timeline_integrity(self) -> List[str]:
        """Validate timeline integrity and return list of issues"""
        issues = []
        
        # Check for circular references
        visited = set()
        
        def check_circular(timeline_id: str, path: List[str]) -> bool:
            if timeline_id in path:
                return True
            if timeline_id in visited:
                return False
                
            visited.add(timeline_id)
            timeline = self.find_timeline_by_id(timeline_id)
            if timeline:
                for child_id in timeline.child_timelines:
                    if check_circular(child_id, path + [timeline_id]):
                        return True
            return False
            
        if check_circular(self.timeline_id, []):
            issues.append("Circular reference detected in timeline hierarchy")
            
        # Check for orphaned nested clips
        for clip in self.get_all_nested_clips():
            if not self.find_timeline_by_id(clip.nested_timeline_id):
                issues.append(f"Clip {clip.clip_id} references non-existent timeline {clip.nested_timeline_id}")
                
        return issues
        
    def clear_render_cache(self):
        """Clear all render caches"""
        for child_timeline in self.child_timelines.values():
            child_timeline.render_cache.clear()
            child_timeline.clear_render_cache()

class NestedTimelineManager:
    """Manager for handling multiple nested timelines"""
    
    def __init__(self):
        self.timelines: Dict[str, NestedTimeline] = {}
        self.active_timeline_id: Optional[str] = None
        
    def create_main_timeline(self, name: str = "Main Timeline") -> str:
        """Create a new main timeline"""
        timeline_id = str(uuid.uuid4())
        timeline = NestedTimeline(timeline_id, TimelineType.MAIN)
        timeline.metadata.name = name
        
        self.timelines[timeline_id] = timeline
        
        if not self.active_timeline_id:
            self.active_timeline_id = timeline_id
            
        return timeline_id
        
    def get_timeline(self, timeline_id: str) -> Optional[NestedTimeline]:
        """Get timeline by ID from anywhere in the hierarchy"""
        for main_timeline in self.timelines.values():
            result = main_timeline.find_timeline_by_id(timeline_id)
            if result:
                return result
        return None
        
    def get_active_timeline(self) -> Optional[NestedTimeline]:
        """Get the currently active timeline"""
        return self.get_timeline(self.active_timeline_id) if self.active_timeline_id else None
        
    def set_active_timeline(self, timeline_id: str) -> bool:
        """Set the active timeline"""
        if self.get_timeline(timeline_id):
            self.active_timeline_id = timeline_id
            return True
        return False
        
    def get_timeline_breadcrumb(self, timeline_id: str) -> List[Tuple[str, str]]:
        """Get breadcrumb path to a timeline (id, name pairs)"""
        timeline = self.get_timeline(timeline_id)
        if not timeline:
            return []
            
        breadcrumb = [(timeline.timeline_id, timeline.metadata.name)]
        
        # Traverse up to root
        current = timeline
        while current.parent_timeline_id:
            parent = self.get_timeline(current.parent_timeline_id)
            if parent:
                breadcrumb.insert(0, (parent.timeline_id, parent.metadata.name))
                current = parent
            else:
                break
                
        return breadcrumb
        
    def export_timeline_structure(self) -> Dict[str, Any]:
        """Export complete timeline structure"""
        return {
            'timelines': {tid: timeline.get_timeline_hierarchy() 
                         for tid, timeline in self.timelines.items()},
            'active_timeline': self.active_timeline_id
        }
        
    def validate_all_timelines(self) -> Dict[str, List[str]]:
        """Validate all timelines and return issues"""
        all_issues = {}
        
        for timeline_id, timeline in self.timelines.items():
            issues = timeline.validate_timeline_integrity()
            if issues:
                all_issues[timeline_id] = issues
                
        return all_issues
