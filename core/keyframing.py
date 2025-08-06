"""
Keyframing module for PyVideoEditor
Handles animation keyframes for video properties
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Dict
import numpy as np
import bisect

@dataclass
class Keyframe:
    """Represents a single keyframe at a given time with a specific value"""
    time: float
    value: float

@dataclass
class KeyframeTrack:
    """Manages keyframes for a specific property"""
    keyframes: List[Keyframe] = field(default_factory=list)

    def add_keyframe(self, time: float, value: float):
        """Add a keyframe or update if it already exists"""
        index = self.find_keyframe_index(time)
        if index is not None:
            # Update value of existing keyframe
            self.keyframes[index].value = value
        else:
            # Insert new keyframe
            bisect.insort(self.keyframes, Keyframe(time, value), key=lambda k: k.time)

    def remove_keyframe(self, time: float):
        """Remove a keyframe at a specific time if exists"""
        index = self.find_keyframe_index(time)
        if index is not None:
            del self.keyframes[index]

    def evaluate(self, time: float, interpolation: str = 'linear') -> float:
        """Evaluate the track value at a specific time using interpolation"""
        if not self.keyframes:
            return 0.0

        # Find position in the keyframe list
        times = [kf.time for kf in self.keyframes]
        
        if time < times[0]:
            return self.keyframes[0].value
        if time >= times[-1]:
            return self.keyframes[-1].value

        # Find surrounding keyframes
        right_index = bisect.bisect_right(times, time)
        left_index = right_index - 1
        left_kf, right_kf = self.keyframes[left_index], self.keyframes[right_index]

        if interpolation == 'linear':
            return np.interp(time, [left_kf.time, right_kf.time], [left_kf.value, right_kf.value])
        else:
            raise NotImplementedError(f"Interpolation method '{interpolation}' not implemented")

    def find_keyframe_index(self, time: float) -> int:
        """Find index of a keyframe at a specific time, or return None"""
        for i, kf in enumerate(self.keyframes):
            if np.isclose(kf.time, time):
                return i
        return None

    def get_keyframes_in_range(self, start_time: float, end_time: float) -> List[Keyframe]:
        """Get all keyframes within a time range"""
        return [kf for kf in self.keyframes if start_time <= kf.time <= end_time]

    def clear(self):
        """Clear all keyframes"""
        self.keyframes.clear()

class AnimatedProperty:
    """Manages animation for different property types"""
    
    def __init__(self, name: str, default_value: float = 0.0):
        self.name = name
        self.default_value = default_value
        
        # Define tracks based on property type
        if name in ['position', 'scale']:
            self.tracks = {'x': KeyframeTrack(), 'y': KeyframeTrack()}
        elif name == 'rotation':
            self.tracks = {'x': KeyframeTrack()}  # Single rotation value
        elif name == 'opacity':
            self.tracks = {'x': KeyframeTrack()}  # Single opacity value
        else:
            self.tracks = {'x': KeyframeTrack()}  # Default single component
    
    def add_keyframe(self, time: float, value, component: str = None):
        """Add keyframe for a property"""
        if isinstance(value, (int, float)):  # Single value
            if component and component in self.tracks:
                self.tracks[component].add_keyframe(time, value)
            else:
                # Default to 'x' component for single values
                self.tracks['x'].add_keyframe(time, value)
        elif isinstance(value, (list, tuple)):  # Multi-component value
            components = ['x', 'y', 'z'][:len(value)]
            for i, val in enumerate(value):
                if components[i] in self.tracks:
                    self.tracks[components[i]].add_keyframe(time, val)
    
    def evaluate(self, time: float):
        """Evaluate property at given time"""
        if len(self.tracks) == 1:
            # Single component property
            return list(self.tracks.values())[0].evaluate(time)
        else:
            # Multi-component property
            return tuple(track.evaluate(time) for track in self.tracks.values())
    
    def remove_keyframe(self, time: float, component: str = None):
        """Remove keyframe at specific time"""
        if component and component in self.tracks:
            self.tracks[component].remove_keyframe(time)
        else:
            # Remove from all tracks
            for track in self.tracks.values():
                track.remove_keyframe(time)

class AnimationManager:
    """Manages animations for video clips"""
    
    def __init__(self):
        self.properties: Dict[str, AnimatedProperty] = {
            'position': AnimatedProperty('position', (0, 0)),
            'scale': AnimatedProperty('scale', (1, 1)),
            'rotation': AnimatedProperty('rotation', 0),
            'opacity': AnimatedProperty('opacity', 1.0)
        }
    
    def add_keyframe(self, property_name: str, time: float, value, component: str = None):
        """Add keyframe for a specific property"""
        if property_name in self.properties:
            self.properties[property_name].add_keyframe(time, value, component)
        else:
            raise ValueError(f"Unknown property: {property_name}")
    
    def remove_keyframe(self, property_name: str, time: float, component: str = None):
        """Remove keyframe for a specific property"""
        if property_name in self.properties:
            self.properties[property_name].remove_keyframe(time, component)
    
    def evaluate_all(self, time: float) -> Dict:
        """Evaluate all properties at given time"""
        return {name: prop.evaluate(time) for name, prop in self.properties.items()}
    
    def evaluate_property(self, property_name: str, time: float):
        """Evaluate specific property at given time"""
        if property_name in self.properties:
            return self.properties[property_name].evaluate(time)
        else:
            raise ValueError(f"Unknown property: {property_name}")
    
    def has_keyframes(self, property_name: str = None) -> bool:
        """Check if there are any keyframes"""
        if property_name:
            if property_name in self.properties:
                return any(track.keyframes for track in self.properties[property_name].tracks.values())
            return False
        else:
            return any(self.has_keyframes(prop) for prop in self.properties.keys())
    
    def clear_all_keyframes(self):
        """Clear all keyframes for all properties"""
        for prop in self.properties.values():
            for track in prop.tracks.values():
                track.clear()
    
    def get_all_keyframe_times(self) -> List[float]:
        """Get all unique keyframe times across all properties"""
        times = set()
        for prop in self.properties.values():
            for track in prop.tracks.values():
                times.update(kf.time for kf in track.keyframes)
        return sorted(list(times))
