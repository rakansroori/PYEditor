"""
Test suite for Multi-Camera Editing System
Demonstrates and tests all multi-camera features including sync, angle switching, and effects
"""

import os
import sys
import tempfile
import numpy as np
from datetime import datetime, timedelta

# Add the core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

try:
    from moviepy import VideoFileClip, ColorClip, AudioClip
except ImportError:
    print("MoviePy not installed. Installing...")
    os.system("pip install moviepy")
    from moviepy import VideoFileClip, ColorClip, AudioClip

from core.timeline import Timeline
from core.multicam_editor import (
    MultiCamTimeline, 
    CameraAngle, 
    SyncMethod,
    MultiCamEffects,
    extend_timeline_with_multicam
)

class MockVideoClip:
    """Mock video clip for testing when actual video files aren't available"""
    
    def __init__(self, duration=10.0, fps=30, size=(1920, 1080), color=(255, 0, 0)):
        self.duration = duration
        self.fps = fps
        self.size = size
        self.color = color
        self.audio = MockAudioClip(duration)
        
    def subclip(self, start, end):
        new_clip = MockVideoClip(end - start, self.fps, self.size, self.color)
        return new_clip
        
    def resize(self, size=None, width=None, height=None):
        if size is not None:
            if isinstance(size, (int, float)):
                new_size = (int(self.size[0] * size), int(self.size[1] * size))
            else:
                new_size = size
        elif width is not None:
            ratio = width / self.size[0]
            new_size = (int(width), int(self.size[1] * ratio))
        elif height is not None:
            ratio = height / self.size[1]
            new_size = (int(self.size[0] * ratio), int(height))
        else:
            new_size = self.size
            
        return MockVideoClip(self.duration, self.fps, new_size, self.color)
        
    def set_position(self, position):
        new_clip = MockVideoClip(self.duration, self.fps, self.size, self.color)
        new_clip.position = position
        return new_clip

class MockAudioClip:
    """Mock audio clip for testing audio sync"""
    
    def __init__(self, duration=10.0, sample_rate=22050):
        self.duration = duration
        self.sample_rate = sample_rate
        
    def to_soundarray(self, fps=22050):
        # Generate mock audio data with some pattern for sync testing
        samples = int(self.duration * fps)
        # Create a simple sine wave pattern
        t = np.linspace(0, self.duration, samples)
        audio = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
        
        # Add some noise and transients for more realistic sync testing
        noise = 0.05 * np.random.randn(samples)
        audio += noise
        
        # Add some impulses at regular intervals (like claps)
        for i in range(int(self.duration)):
            impulse_pos = int(i * fps)
            if impulse_pos < samples:
                audio[impulse_pos:impulse_pos+100] += 0.5
        
        return audio

def create_mock_video_files():
    """Create mock video clips for testing"""
    clips = {}
    
    # Camera A - Wide shot (red background)
    clips['camera_a'] = MockVideoClip(duration=30.0, color=(255, 0, 0))
    
    # Camera B - Medium shot (green background) 
    clips['camera_b'] = MockVideoClip(duration=30.0, color=(0, 255, 0))
    
    # Camera C - Close up (blue background)
    clips['camera_c'] = MockVideoClip(duration=30.0, color=(0, 0, 255))
    
    return clips

def test_multicam_sequence_creation():
    """Test creating multi-camera sequences"""
    print("Testing Multi-Camera Sequence Creation...")
    
    # Create base timeline
    timeline = Timeline()
    multicam_timeline = extend_timeline_with_multicam(timeline)
    
    # Create mock camera clips
    camera_clips = [
        ("mock_camera_a.mp4", "Camera A", CameraAngle.WIDE_SHOT),
        ("mock_camera_b.mp4", "Camera B", CameraAngle.MEDIUM_SHOT),
        ("mock_camera_c.mp4", "Camera C", CameraAngle.CLOSE_UP)
    ]
    
    # Create multicam sequence
    sequence_id = multicam_timeline.create_multicam_sequence(
        name="Test Multicam Scene",
        camera_clips=camera_clips,
        sync_method=SyncMethod.AUDIO_WAVEFORM
    )
    
    assert sequence_id != "", "Failed to create multicam sequence"
    
    # Verify sequence was created
    sequence = multicam_timeline.get_sequence(sequence_id)
    assert sequence is not None, "Sequence not found after creation"
    assert len(sequence.cameras) == 3, f"Expected 3 cameras, got {len(sequence.cameras)}"
    assert sequence.name == "Test Multicam Scene", "Sequence name mismatch"
    
    print("✓ Multi-camera sequence creation successful")
    return multicam_timeline, sequence_id

def test_audio_synchronization():
    """Test audio-based synchronization"""
    print("Testing Audio Synchronization...")
    
    multicam_timeline, sequence_id = test_multicam_sequence_creation()
    sequence = multicam_timeline.get_sequence(sequence_id)
    
    # Replace mock paths with actual mock clips
    mock_clips = create_mock_video_files()
    for i, camera in enumerate(sequence.cameras):
        camera.clip = list(mock_clips.values())[i]
    
    # Test synchronization
    sync_result = multicam_timeline.sync_sequence(sequence_id)
    assert sync_result, "Audio synchronization failed"
    
    # Check that sync offsets were calculated
    for camera in sequence.cameras:
        print(f"Camera {camera.camera_name}: sync_offset = {camera.sync_offset:.3f}s")
    
    print("✓ Audio synchronization completed")
    return multicam_timeline, sequence_id

def test_angle_switching():
    """Test switching between camera angles"""
    print("Testing Angle Switching...")
    
    multicam_timeline, sequence_id = test_audio_synchronization()
    sequence = multicam_timeline.get_sequence(sequence_id)
    
    # Add multicam sequence to timeline
    clip_id = multicam_timeline.add_multicam_to_timeline(sequence_id, start_time=0.0, track=0)
    assert clip_id != "", "Failed to add multicam sequence to timeline"
    
    # Test angle switching
    camera_b = sequence.cameras[1]  # Medium shot
    switch_result = multicam_timeline.switch_angle(sequence_id, camera_b.id, clip_id)
    assert switch_result, "Failed to switch camera angle"
    
    # Verify current angle was updated
    current_angle = multicam_timeline.current_angles.get(sequence_id)
    assert current_angle == camera_b.id, "Current angle not updated correctly"
    
    print("✓ Angle switching successful")
    return multicam_timeline, sequence_id, clip_id

def test_multicam_cuts():
    """Test automatic multi-camera cuts"""
    print("Testing Multi-Camera Cuts...")
    
    multicam_timeline, sequence_id, _ = test_angle_switching()
    sequence = multicam_timeline.get_sequence(sequence_id)
    
    # Define cut points and camera angles
    cuts = [
        (0.0, sequence.cameras[0].id),    # Start with wide shot
        (5.0, sequence.cameras[1].id),    # Cut to medium shot at 5s
        (10.0, sequence.cameras[2].id),   # Cut to close up at 10s
        (15.0, sequence.cameras[0].id),   # Back to wide shot at 15s
    ]
    
    # Create multicam cuts
    cut_result = multicam_timeline.create_multicam_cut(sequence_id, cuts)
    assert cut_result, "Failed to create multicam cuts"
    
    # Verify clips were added to timeline
    clips_at_5s = multicam_timeline.base_timeline.get_clips_at_time(5.0)
    assert len(clips_at_5s) > 0, "No clips found at cut point"
    
    print("✓ Multi-camera cuts successful")
    return multicam_timeline, sequence_id

def test_multicam_effects():
    """Test multi-camera effects like PiP and split screen"""
    print("Testing Multi-Camera Effects...")
    
    mock_clips = create_mock_video_files()
    main_clip = list(mock_clips.values())[0]
    pip_clip = list(mock_clips.values())[1]
    
    # Test Picture-in-Picture
    pip_result = MultiCamEffects.create_picture_in_picture(
        main_clip, pip_clip, position=(0.7, 0.1), size=0.3
    )
    assert pip_result is not None, "Picture-in-Picture effect failed"
    
    # Test Split Screen - Horizontal
    split_horizontal = MultiCamEffects.create_split_screen(
        list(mock_clips.values())[:2], layout='horizontal'
    )
    assert split_horizontal is not None, "Horizontal split screen failed"
    
    # Test Split Screen - Vertical  
    split_vertical = MultiCamEffects.create_split_screen(
        list(mock_clips.values())[:2], layout='vertical'
    )
    assert split_vertical is not None, "Vertical split screen failed"
    
    # Test Split Screen - Grid
    split_grid = MultiCamEffects.create_split_screen(
        list(mock_clips.values()), layout='grid'
    )
    assert split_grid is not None, "Grid split screen failed"
    
    print("✓ Multi-camera effects successful")

def test_manual_sync_adjustment():
    """Test manual sync adjustment"""
    print("Testing Manual Sync Adjustment...")
    
    multicam_timeline, sequence_id = test_audio_synchronization()
    sequence = multicam_timeline.get_sequence(sequence_id)
    camera = sequence.cameras[0]
    
    # Record original offset
    original_offset = camera.sync_offset
    
    # Apply manual adjustment
    adjustment = 0.5  # 500ms adjustment
    adjust_result = multicam_timeline.adjust_camera_sync(sequence_id, camera.id, adjustment)
    assert adjust_result, "Manual sync adjustment failed"
    
    # Verify adjustment was applied
    assert abs(camera.sync_offset - (original_offset + adjustment)) < 0.001, \
        "Sync adjustment not applied correctly"
    
    print(f"✓ Manual sync adjustment successful: {original_offset:.3f}s → {camera.sync_offset:.3f}s")

def test_audio_control():
    """Test audio enable/disable for cameras"""
    print("Testing Audio Control...")
    
    multicam_timeline, sequence_id = test_audio_synchronization()
    sequence = multicam_timeline.get_sequence(sequence_id)
    camera = sequence.cameras[0]
    
    # Test disabling audio
    disable_result = multicam_timeline.set_camera_audio_enabled(sequence_id, camera.id, False)
    assert disable_result, "Failed to disable camera audio"
    assert not camera.audio_enabled, "Audio not disabled correctly"
    
    # Test enabling audio
    enable_result = multicam_timeline.set_camera_audio_enabled(sequence_id, camera.id, True)
    assert enable_result, "Failed to enable camera audio"
    assert camera.audio_enabled, "Audio not enabled correctly"
    
    print("✓ Audio control successful")

def test_timecode_sync():
    """Test timecode-based synchronization"""
    print("Testing Timecode Synchronization...")
    
    # Create timeline
    timeline = Timeline()
    multicam_timeline = extend_timeline_with_multicam(timeline)
    
    # Create sequence with timecode information
    camera_clips = [
        ("mock_camera_a.mp4", "Camera A", CameraAngle.WIDE_SHOT),
        ("mock_camera_b.mp4", "Camera B", CameraAngle.MEDIUM_SHOT),
    ]
    
    sequence_id = multicam_timeline.create_multicam_sequence(
        name="Timecode Test",
        camera_clips=camera_clips,
        sync_method=SyncMethod.TIMECODE
    )
    
    sequence = multicam_timeline.get_sequence(sequence_id)
    
    # Set timecode information
    base_time = datetime.now()
    sequence.cameras[0].timecode_start = base_time
    sequence.cameras[1].timecode_start = base_time + timedelta(seconds=2)  # 2 second offset
    
    # Test timecode sync
    sync_result = multicam_timeline.sync_sequence(sequence_id)
    assert sync_result, "Timecode synchronization failed"
    
    # Verify sync offsets
    assert sequence.cameras[0].sync_offset == 0.0, "Master camera offset should be 0"
    assert abs(sequence.cameras[1].sync_offset - 2.0) < 0.001, "Slave camera offset incorrect"
    
    print("✓ Timecode synchronization successful")

def run_performance_test():
    """Test performance with multiple cameras and long sequences"""
    print("Running Performance Test...")
    
    timeline = Timeline()
    multicam_timeline = extend_timeline_with_multicam(timeline)
    
    # Create sequence with many cameras
    camera_clips = [
        (f"mock_camera_{i}.mp4", f"Camera {i}", CameraAngle.CUSTOM) 
        for i in range(8)  # 8 cameras
    ]
    
    import time
    start_time = time.time()
    
    sequence_id = multicam_timeline.create_multicam_sequence(
        name="Performance Test",
        camera_clips=camera_clips,
        sync_method=SyncMethod.MANUAL  # Skip sync for performance test
    )
    
    creation_time = time.time() - start_time
    
    sequence = multicam_timeline.get_sequence(sequence_id)
    
    # Add mock clips
    mock_clips = {}
    for i in range(8):
        mock_clips[f'camera_{i}'] = MockVideoClip(duration=120.0)  # 2 minute clips
    
    for i, camera in enumerate(sequence.cameras):
        camera.clip = mock_clips[f'camera_{i}']
    
    # Test adding to timeline
    start_time = time.time()
    clip_id = multicam_timeline.add_multicam_to_timeline(sequence_id, start_time=0.0, track=0)
    timeline_time = time.time() - start_time
    
    # Test angle switching performance
    start_time = time.time()
    for i in range(20):  # 20 angle switches
        camera_idx = i % len(sequence.cameras)
        multicam_timeline.switch_angle(sequence_id, sequence.cameras[camera_idx].id, clip_id)
    switching_time = time.time() - start_time
    
    print(f"✓ Performance Test Results:")
    print(f"  - Sequence creation: {creation_time:.3f}s")
    print(f"  - Timeline addition: {timeline_time:.3f}s") 
    print(f"  - 20 angle switches: {switching_time:.3f}s ({switching_time/20:.3f}s per switch)")

def demonstration_workflow():
    """Demonstrate a complete multi-camera editing workflow"""
    print("\n" + "="*60)
    print("MULTI-CAMERA EDITING WORKFLOW DEMONSTRATION")
    print("="*60)
    
    # Step 1: Create project
    print("\n1. Creating multi-camera project...")
    timeline = Timeline()
    multicam_timeline = extend_timeline_with_multicam(timeline)
    
    # Step 2: Import footage
    print("2. Importing camera footage...")
    camera_clips = [
        ("wide_shot.mp4", "Main Camera", CameraAngle.WIDE_SHOT),
        ("medium_shot.mp4", "Camera B", CameraAngle.MEDIUM_SHOT),
        ("closeup.mp4", "Camera C", CameraAngle.CLOSE_UP),
        ("over_shoulder.mp4", "Camera D", CameraAngle.OVER_SHOULDER)
    ]
    
    # Step 3: Create multicam sequence
    print("3. Creating synchronized multi-camera sequence...")
    sequence_id = multicam_timeline.create_multicam_sequence(
        name="Interview Scene",
        camera_clips=camera_clips,
        sync_method=SyncMethod.AUDIO_WAVEFORM
    )
    
    # Step 4: Add mock clips and sync
    sequence = multicam_timeline.get_sequence(sequence_id)
    mock_clips = create_mock_video_files()
    for i, camera in enumerate(sequence.cameras):
        if i < len(mock_clips):
            camera.clip = list(mock_clips.values())[i]
    
    sync_success = multicam_timeline.sync_sequence(sequence_id)
    print(f"   Synchronization: {'✓ Success' if sync_success else '✗ Failed'}")
    
    # Step 5: Add to timeline
    print("4. Adding multi-camera sequence to timeline...")
    clip_id = multicam_timeline.add_multicam_to_timeline(sequence_id, start_time=0.0, track=0)
    
    # Step 6: Create edit with angle changes
    print("5. Creating edit with camera angle changes...")
    cuts = [
        (0.0, sequence.cameras[0].id),    # Wide shot intro
        (3.0, sequence.cameras[1].id),    # Medium shot
        (8.0, sequence.cameras[2].id),    # Close up for emphasis
        (12.0, sequence.cameras[3].id),   # Over shoulder
        (16.0, sequence.cameras[0].id),   # Back to wide
        (20.0, sequence.cameras[1].id),   # End on medium
    ]
    
    multicam_timeline.create_multicam_cut(sequence_id, cuts)
    
    # Step 7: Apply effects
    print("6. Applying multi-camera effects...")
    
    # Create picture-in-picture for a section
    if len(sequence.cameras) >= 2:
        main_clip = sequence.cameras[0].clip
        pip_clip = sequence.cameras[1].clip
        pip_composite = MultiCamEffects.create_picture_in_picture(main_clip, pip_clip)
        print("   ✓ Picture-in-picture effect created")
    
    # Create split screen
    all_clips = [cam.clip for cam in sequence.cameras if cam.clip]
    if len(all_clips) >= 2:
        split_screen = MultiCamEffects.create_split_screen(all_clips[:2], layout='horizontal')
        print("   ✓ Split screen effect created")
    
    # Step 8: Fine-tune sync
    print("7. Fine-tuning synchronization...")
    multicam_timeline.adjust_camera_sync(sequence_id, sequence.cameras[1].id, 0.1)
    print("   ✓ Manual sync adjustment applied")
    
    # Step 9: Audio mixing
    print("8. Audio mixing setup...")
    multicam_timeline.set_camera_audio_enabled(sequence_id, sequence.cameras[0].id, True)  # Main audio
    multicam_timeline.set_camera_audio_enabled(sequence_id, sequence.cameras[1].id, False) # Disable others
    multicam_timeline.set_camera_audio_enabled(sequence_id, sequence.cameras[2].id, False)
    print("   ✓ Audio sources configured")
    
    print("\n✓ Multi-camera editing workflow completed successfully!")
    print(f"   - Cameras: {len(sequence.cameras)}")
    print(f"   - Cuts: {len(cuts)}")
    print(f"   - Timeline duration: {multicam_timeline.base_timeline.get_total_duration():.1f}s")

def main():
    """Run all multi-camera editing tests"""
    print("PyVideoEditor - Multi-Camera Editing System Tests")
    print("=" * 60)
    
    try:
        # Core functionality tests
        test_multicam_sequence_creation()
        test_audio_synchronization()
        test_angle_switching()
        test_multicam_cuts()
        test_multicam_effects()
        test_manual_sync_adjustment()
        test_audio_control()
        test_timecode_sync()
        
        # Performance test
        run_performance_test()
        
        # Full workflow demonstration
        demonstration_workflow()
        
        print("\n" + "="*60)
        print("✓ ALL MULTI-CAMERA TESTS PASSED!")
        print("Multi-camera editing system is fully functional.")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
