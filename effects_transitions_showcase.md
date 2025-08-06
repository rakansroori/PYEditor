
# PyVideoEditor - Advanced Effects & Transitions Showcase

## Available Video Effects

### Blur Effect
- **ID**: `blur`
- **Description**: Professional blur effect
- **Parameters**: `strength` (float, default: 1.0)

### Brightness Effect
- **ID**: `brightness`
- **Description**: Professional brightness effect
- **Parameters**: `brightness` (float, default: 1.2)

### Contrast Effect
- **ID**: `contrast`
- **Description**: Professional contrast effect
- **Parameters**: `contrast` (float, default: 1.5)

### Sepia Effect
- **ID**: `sepia`
- **Description**: Professional sepia effect

### Sharpen Effect
- **ID**: `sharpen`
- **Description**: Professional sharpen effect
- **Parameters**: `strength` (float, default: 1.0)

### Vignette Effect
- **ID**: `vignette`
- **Description**: Professional vignette effect
- **Parameters**: `strength` (float, default: 0.5)

### Noise Effect
- **ID**: `noise`
- **Description**: Professional noise effect
- **Parameters**: `amount` (float, default: 0.1)

### Pixelate Effect
- **ID**: `pixelate`
- **Description**: Professional pixelate effect
- **Parameters**: `pixel_size` (int, default: 10)

### Edge Detection Effect
- **ID**: `edge_detection`
- **Description**: Professional edge_detection effect
- **Parameters**: `threshold1` (int, default: 100), `threshold2` (int, default: 200)

### Rotate_3d
- **Error**: 'NoneType' object is not callable

### Cube_3d
- **Error**: 'NoneType' object is not callable

### Cylinder_3d
- **Error**: 'NoneType' object is not callable

### Sphere_3d
- **Error**: 'NoneType' object is not callable

### Wave_deform_3d
- **Error**: 'NoneType' object is not callable

### Ripple_3d
- **Error**: 'NoneType' object is not callable

### Depth_of_field_3d
- **Error**: 'NoneType' object is not callable


## Available Video Transitions

### Crossfade
- **ID**: `crossfade`
- **Description**: Professional crossfade transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Slide Left
- **ID**: `slide_left`
- **Description**: Professional slide left transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Slide Right
- **ID**: `slide_right`
- **Description**: Professional slide right transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Slide Up
- **ID**: `slide_up`
- **Description**: Professional slide up transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Slide Down
- **ID**: `slide_down`
- **Description**: Professional slide down transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Wipe Horizontal
- **ID**: `wipe_horizontal`
- **Description**: Professional wipe horizontal transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Wipe Vertical
- **ID**: `wipe_vertical`
- **Description**: Professional wipe vertical transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Fade to Black
- **ID**: `fade_to_black`
- **Description**: Professional fade to black transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Zoom In
- **ID**: `zoom_in`
- **Description**: Professional zoom in transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Zoom Out
- **ID**: `zoom_out`
- **Description**: Professional zoom out transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Circular Wipe
- **ID**: `circular_wipe`
- **Description**: Professional circular wipe transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Push Left
- **ID**: `push_left`
- **Description**: Professional push left transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Push Right
- **ID**: `push_right`
- **Description**: Professional push right transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Push Up
- **ID**: `push_up`
- **Description**: Professional push up transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Push Down
- **ID**: `push_down`
- **Description**: Professional push down transition
- **Parameters**: `duration` (float, transition duration in seconds)

### Rotate
- **ID**: `rotate`
- **Description**: Professional rotate transition
- **Parameters**: `duration` (float, transition duration in seconds)


## Usage Examples

### Applying Effects in Code
```python
from core.video_processor import VideoProcessor

# Initialize processor
processor = VideoProcessor()

# Load a video
processor.load_video("sample_video.mp4")

# Apply blur effect
processed_clip = processor.apply_effect_to_clip(
    processor.current_clip, 
    'blur', 
    strength=2.0
)

# Apply multiple effects
processed_clip = processor.apply_effect_to_clip(processed_clip, 'brightness', brightness=1.3)
processed_clip = processor.apply_effect_to_clip(processed_clip, 'vignette', strength=0.6)
```

### Applying Transitions in Code
```python
# Apply transition between two clips
clip1 = processor.current_clip.subclip(0, 5)
clip2 = processor.current_clip.subclip(5, 10)

transitioned_clip = processor.apply_transition_between_clips(
    clip1, 
    clip2, 
    'crossfade', 
    duration=1.0
)
```

### Using the UI
1. Load a video file using File > Import Media
2. Select an effect from the Effects panel
3. Click "Apply Selected Effect"
4. Select a transition from the Transitions panel
5. Click "Apply Selected Transition" (for demonstration)

## Technical Notes

- All effects are applied in real-time using MoviePy
- Effects can be stacked and combined
- Transitions work between any two video clips
- Parameters can be customized for each effect
- GPU acceleration is available for supported effects

