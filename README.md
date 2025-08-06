# PyVideoEditor - Professional Video Editor

A professional-grade video editor built with Python, featuring advanced video processing, color grading, and audio editing capabilities.

## Features

### ✅ Implemented Features

#### 1. Color Grading
- **Hue Adjustment**: Real-time hue shifting (-180 to +180 degrees)
- **Saturation Control**: Enhance or reduce color saturation (0-200%)
- **Luminance Adjustment**: Control brightness and contrast (0-200%)
- **Real-time Preview**: See changes instantly as you adjust sliders
- **Reset Functionality**: Quickly revert to original settings

#### 2. Audio Editing
- **Waveform Visualization**: Real-time audio waveform display using matplotlib
- **Volume Control**: Precise volume adjustment (0-200%)
- **Audio Effects**:
  - Echo effect with configurable delay and decay
  - Audio normalization to prevent clipping
  - Fade in/out effects
- **Multi-format Support**: Works with various audio formats through MoviePy

#### 3. Core Video Processing
- **Video Loading**: Support for MP4, AVI, MOV, MKV, WMV formats
- **Video Export**: High-quality export with customizable codecs and bitrates
- **Timeline Management**: Advanced timeline with multiple tracks support
- **Clip Operations**: Trim, split, duplicate, and move clips
- **Preview System**: Real-time video preview functionality

#### 4. Video Effects & Transitions
- **Basic Effects**: Fade in/out, brightness, contrast adjustments
- **Advanced Effects**: Blur, sepia tone, and custom pixel manipulations
- **Transitions**: Crossfade, slide, wipe, and fade-to-black transitions
- **Plugin System**: Extensible architecture for custom effects

#### 5. Professional UI
- **Modern Interface**: Clean, professional PyQt6-based interface
- **Organized Controls**: Grouped controls for easy navigation
- **Real-time Feedback**: Live preview and status updates
- **File Management**: Integrated file browser for media import/export

#### 6. Keyframing System ✅
- **Property Animation**: Animate position, scale, rotation, and opacity over time
- **Linear Interpolation**: Smooth transitions between keyframes
- **Timeline Integration**: Keyframes integrated with timeline clips
- **Multi-component Support**: Handle both single and multi-dimensional properties
- **Real-time Preview**: See animations applied in real-time
- **Keyframe Management**: Add, remove, and modify keyframes easily

#### 7. Chroma Key (Green Screen) ✅
- **Background Replacement**: Replace green/blue screen with images or videos
- **Advanced Masking**: HSV-based color detection with morphological operations
- **Spill Suppression**: Reduce color bleeding from key colors
- **Edge Softening**: Smooth edges with Gaussian blur
- **Multiple Presets**: Green screen, blue screen, red screen, high quality, fast processing
- **Tolerance Control**: Adjustable color tolerance for different lighting conditions
- **Real-time Preview**: See chroma key effects applied in real-time

#### 8. Title and Text System ✅
- **Professional Text Overlays**: Add styled text with customizable fonts, colors, and effects
- **Text Animation**: Fade in/out, slide effects, typewriter animation, scaling, and more
- **Template System**: Pre-built templates for titles, subtitles, lower thirds, and custom designs
- **Advanced Styling**: Font selection, stroke, shadows, backgrounds, alignment control
- **Motion Graphics**: Create animated title sequences with multiple text elements
- **Template Management**: Save, load, and share custom text templates
- **Real-time Integration**: Text overlays composite seamlessly with video content

### 🚧 Planned Features (Roadmap)

#### 5. Advanced Timeline
- Nested timelines
- Track grouping and locking
- Magnetic timeline with snapping

#### 6. 3D Effects
- 3D text and titles
- Basic 3D transformations
- Animated 3D paths

#### 7. Collaboration Features
- Cloud project sync
- Real-time collaborative editing
- Version control

#### 8. AI-Powered Features
- Automated scene detection
- Content-aware editing
- Smart transitions

## Installation

### Prerequisites
- Python 3.10+ (tested with Python 3.13)
- FFmpeg (for video processing)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/PyVideoEditor.git
   cd PyVideoEditor
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python -m ui.main_window
   ```

## Usage

### Basic Workflow

1. **Load a Video**:
   - Click "Load Video" button
   - Select your video file from the file dialog
   - The video will load and audio waveform will display

2. **Apply Color Grading**:
   - Use the Hue slider to adjust color temperature
   - Adjust Saturation for color intensity
   - Control Luminance for brightness
   - Click "Reset Color Grading" to revert changes

3. **Edit Audio**:
   - Adjust volume with the Volume slider
   - Apply echo effect with "Apply Echo" button
   - Normalize audio levels with "Normalize Audio"
   - View real-time waveform changes

4. **Preview and Export**:
   - Click "Play Preview" to preview your video
   - Click "Export Video" to save your edited video
   - Choose format and location for export

5. **Create Keyframe Animations**:
   - Click "Add Keyframe" to create position animations
   - Use "Remove Keyframe" to delete keyframes
   - Preview shows animations in real-time

### Advanced Features

#### Using Effects
```python
# Apply custom effects programmatically
from core.video_processor import VideoProcessor
from plugins.effects import EffectsManager

processor = VideoProcessor()
effects = EffectsManager()

# Load video
processor.load_video("input.mp4")

# Apply blur effect
processor.current_clip = effects.apply_effect(
    processor.current_clip, 
    "blur", 
    strength=2.0
)
```

#### Custom Transitions
```python
from plugins.transitions import TransitionsManager

transitions = TransitionsManager()

# Apply crossfade between clips
result = transitions.apply_transition(
    clip1, clip2, 
    transition_name="crossfade", 
    duration=1.0
)
```

#### Keyframe Animation
```python
from core.timeline import Timeline

timeline = Timeline()

# Add video clip to timeline
clip_id = timeline.add_clip(my_video_clip, start_time=0, track=0)

# Add keyframes for position animation
timeline.add_keyframe_to_clip(clip_id, 'position', 0.0, (0, 0))     # Start at origin
timeline.add_keyframe_to_clip(clip_id, 'position', 2.0, (100, 50))  # Move to (100, 50) at 2s
timeline.add_keyframe_to_clip(clip_id, 'position', 4.0, (200, 100)) # Move to (200, 100) at 4s

# Add opacity animation
timeline.add_keyframe_to_clip(clip_id, 'opacity', 0.0, 1.0)  # Fully visible at start
timeline.add_keyframe_to_clip(clip_id, 'opacity', 1.0, 0.5)  # Half transparent at 1s
timeline.add_keyframe_to_clip(clip_id, 'opacity', 2.0, 1.0)  # Fully visible at 2s

# Render frame with animations at specific time
animated_frame = timeline.render_frame_at_time(1.5)
```

#### Text Overlays and Titles
```python
from core.text_system import TitleSystem, TextStyle, TextAnimationConfig, TextAnimation
from core.video_processor import VideoProcessor

# Initialize systems
processor = VideoProcessor()
title_system = TitleSystem()

# Load video
processor.load_video("input.mp4")

# Add simple text overlay using template
processor.add_text_overlay(
    text="Welcome to My Video",
    template_name="main_title",
    duration=3.0,
    position=('center', 'top')
)

# Create custom styled text
custom_style = TextStyle(
    font="Impact",
    font_size=64,
    color="red",
    stroke_color="white",
    stroke_width=2,
    bold=True
)

custom_animation = TextAnimationConfig(
    animation_type=TextAnimation.TYPEWRITER,
    duration=2.0
)

text_overlay = title_system.create_text_overlay(
    text="Breaking News!",
    custom_style=custom_style,
    custom_animation=custom_animation,
    duration=5.0
)

# Create title sequence
titles = [
    {
        'text': 'Chapter 1',
        'template': 'main_title',
        'start_time': 0.0,
        'duration': 3.0,
        'position': ('center', 'center')
    },
    {
        'text': 'The Beginning',
        'template': 'subtitle', 
        'start_time': 2.0,
        'duration': 4.0,
        'position': ('center', 'bottom')
    }
]

processor.create_title_sequence(titles)
```

## Architecture

### Project Structure
```
PyVideoEditor/
├── core/                    # Core processing modules
│   ├── video_processor.py   # Main video processing
│   ├── color_grading.py     # Color grading functionality
│   ├── audio_editing.py     # Audio processing and effects
│   └── timeline.py          # Timeline management
├── ui/                      # User interface
│   └── main_window.py       # Main application window
├── plugins/                 # Extensible plugin system
│   ├── effects.py           # Video effects plugins
│   └── transitions.py       # Transition effects
├── tests/                   # Unit tests
│   ├── test_video_processor.py
│   └── test_audio_editing.py
└── assets/                  # Media assets for testing
```

### Key Technologies
- **VideoProcessing**: MoviePy for video manipulation
- **UI Framework**: PyQt6 for modern, native interface
- **Image Processing**: OpenCV for advanced video effects
- **Audio Visualization**: Matplotlib for waveform display
- **Testing**: pytest for comprehensive test coverage

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_video_processor.py -v

# Run with coverage
python -m pytest tests/ --cov=core --cov-report=html
```

### Adding New Effects
1. Create effect class inheriting from `VideoEffect`
2. Implement `apply()` and `get_name()` methods
3. Register in `EffectsManager`
4. Add tests in `tests/` directory

Example:
```python
class CustomEffect(VideoEffect):
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        # Your effect implementation
        return modified_clip
    
    def get_name(self) -> str:
        return "Custom Effect"
```

### Code Style
- Follow PEP 8 standards
- Use type hints for better code maintainability
- Document all public methods and classes
- Maintain test coverage above 80%

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **MoviePy**: Core video processing capabilities
- **OpenCV**: Computer vision and image processing
- **PyQt6**: Professional desktop application framework
- **FFmpeg**: Multimedia framework for encoding/decoding

## Support

For support, feature requests, or bug reports:
- Open an issue on GitHub
- Check the documentation in `/docs`
- Review existing tests for usage examples

---

**PyVideoEditor** - Bringing professional video editing to Python developers and content creators.
