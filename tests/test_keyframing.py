import pytest
import numpy as np
from core.keyframing import Keyframe, KeyframeTrack, AnimatedProperty, AnimationManager

class TestKeyframe:
    def test_keyframe_creation(self):
        """Test keyframe creation"""
        kf = Keyframe(time=1.0, value=10.0)
        assert kf.time == 1.0
        assert kf.value == 10.0

class TestKeyframeTrack:
    def setup_method(self):
        self.track = KeyframeTrack()

    def test_add_keyframe(self):
        """Test adding keyframes"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        
        assert len(self.track.keyframes) == 2
        assert self.track.keyframes[0].time == 1.0
        assert self.track.keyframes[1].time == 2.0

    def test_add_keyframe_sorted(self):
        """Test keyframes are added in sorted order"""
        self.track.add_keyframe(3.0, 30.0)
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        
        times = [kf.time for kf in self.track.keyframes]
        assert times == [1.0, 2.0, 3.0]

    def test_update_existing_keyframe(self):
        """Test updating existing keyframe"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(1.0, 15.0)  # Update same time
        
        assert len(self.track.keyframes) == 1
        assert self.track.keyframes[0].value == 15.0

    def test_remove_keyframe(self):
        """Test removing keyframes"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        
        self.track.remove_keyframe(1.0)
        assert len(self.track.keyframes) == 1
        assert self.track.keyframes[0].time == 2.0

    def test_evaluate_no_keyframes(self):
        """Test evaluation with no keyframes"""
        result = self.track.evaluate(1.0)
        assert result == 0.0

    def test_evaluate_single_keyframe(self):
        """Test evaluation with single keyframe"""
        self.track.add_keyframe(1.0, 10.0)
        
        assert self.track.evaluate(0.5) == 10.0  # Before
        assert self.track.evaluate(1.0) == 10.0  # At
        assert self.track.evaluate(1.5) == 10.0  # After

    def test_evaluate_linear_interpolation(self):
        """Test linear interpolation between keyframes"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(3.0, 30.0)
        
        # Test interpolation at midpoint
        result = self.track.evaluate(2.0)
        assert result == 20.0
        
        # Test at keyframe positions
        assert self.track.evaluate(1.0) == 10.0
        assert self.track.evaluate(3.0) == 30.0
        
        # Test outside range
        assert self.track.evaluate(0.5) == 10.0  # Before first
        assert self.track.evaluate(4.0) == 30.0  # After last

    def test_find_keyframe_index(self):
        """Test finding keyframe indices"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        
        assert self.track.find_keyframe_index(1.0) == 0
        assert self.track.find_keyframe_index(2.0) == 1
        assert self.track.find_keyframe_index(1.5) is None

    def test_get_keyframes_in_range(self):
        """Test getting keyframes within time range"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        self.track.add_keyframe(3.0, 30.0)
        
        keyframes = self.track.get_keyframes_in_range(1.5, 2.5)
        assert len(keyframes) == 1
        assert keyframes[0].time == 2.0

    def test_clear(self):
        """Test clearing all keyframes"""
        self.track.add_keyframe(1.0, 10.0)
        self.track.add_keyframe(2.0, 20.0)
        
        self.track.clear()
        assert len(self.track.keyframes) == 0

class TestAnimatedProperty:
    def test_single_component_property(self):
        """Test single component property (like opacity)"""
        prop = AnimatedProperty('opacity', 1.0)
        
        prop.add_keyframe(1.0, 0.5)
        prop.add_keyframe(2.0, 1.0)
        
        # Should return single value
        result = prop.evaluate(1.5)
        assert isinstance(result, float)
        assert result == 0.75  # Linear interpolation

    def test_multi_component_property(self):
        """Test multi-component property (like position)"""
        prop = AnimatedProperty('position', (0, 0))
        
        prop.add_keyframe(1.0, (10, 20))
        prop.add_keyframe(2.0, (30, 40))
        
        # Should return tuple
        result = prop.evaluate(1.5)
        assert isinstance(result, tuple)
        assert result == (20.0, 30.0)  # Linear interpolation

    def test_component_specific_keyframe(self):
        """Test adding keyframe to specific component"""
        prop = AnimatedProperty('position', (0, 0))
        
        prop.add_keyframe(1.0, 10, 'x')
        prop.add_keyframe(1.0, 20, 'y')
        
        result = prop.evaluate(1.0)
        assert result == (10.0, 20.0)

    def test_remove_keyframe_all_components(self):
        """Test removing keyframe from all components"""
        prop = AnimatedProperty('position', (0, 0))
        
        prop.add_keyframe(1.0, (10, 20))
        prop.remove_keyframe(1.0)
        
        # Should have default values
        result = prop.evaluate(1.0)
        assert result == (0.0, 0.0)

class TestAnimationManager:
    def setup_method(self):
        self.manager = AnimationManager()

    def test_initialization(self):
        """Test animation manager initialization"""
        assert 'position' in self.manager.properties
        assert 'scale' in self.manager.properties
        assert 'rotation' in self.manager.properties
        assert 'opacity' in self.manager.properties

    def test_add_keyframe(self):
        """Test adding keyframes through manager"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        self.manager.add_keyframe('opacity', 1.0, 0.5)
        
        assert self.manager.has_keyframes('position')
        assert self.manager.has_keyframes('opacity')

    def test_remove_keyframe(self):
        """Test removing keyframes through manager"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        self.manager.remove_keyframe('position', 1.0)
        
        assert not self.manager.has_keyframes('position')

    def test_evaluate_all_properties(self):
        """Test evaluating all properties"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        self.manager.add_keyframe('opacity', 1.0, 0.5)
        
        result = self.manager.evaluate_all(1.0)
        
        assert 'position' in result
        assert 'opacity' in result
        assert result['position'] == (10.0, 20.0)
        assert result['opacity'] == 0.5

    def test_evaluate_specific_property(self):
        """Test evaluating specific property"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        
        result = self.manager.evaluate_property('position', 1.0)
        assert result == (10.0, 20.0)

    def test_has_keyframes(self):
        """Test checking for keyframes"""
        assert not self.manager.has_keyframes()
        assert not self.manager.has_keyframes('position')
        
        self.manager.add_keyframe('position', 1.0, (10, 20))
        
        assert self.manager.has_keyframes()
        assert self.manager.has_keyframes('position')
        assert not self.manager.has_keyframes('scale')

    def test_clear_all_keyframes(self):
        """Test clearing all keyframes"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        self.manager.add_keyframe('opacity', 1.0, 0.5)
        
        self.manager.clear_all_keyframes()
        
        assert not self.manager.has_keyframes()

    def test_get_all_keyframe_times(self):
        """Test getting all keyframe times"""
        self.manager.add_keyframe('position', 1.0, (10, 20))
        self.manager.add_keyframe('position', 3.0, (30, 40))
        self.manager.add_keyframe('opacity', 2.0, 0.5)
        
        times = self.manager.get_all_keyframe_times()
        assert times == [1.0, 2.0, 3.0]

    def test_unknown_property_error(self):
        """Test error handling for unknown properties"""
        with pytest.raises(ValueError, match="Unknown property"):
            self.manager.add_keyframe('unknown', 1.0, 10)
        
        with pytest.raises(ValueError, match="Unknown property"):
            self.manager.evaluate_property('unknown', 1.0)
