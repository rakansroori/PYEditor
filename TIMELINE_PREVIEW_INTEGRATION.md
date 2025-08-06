# Timeline-Preview Integration

## Overview
The PyVideoEditor now has full integration between the timeline and preview widgets, allowing for seamless editing and playback.

## How It Works

### 1. **Media Loading**
- Media files are loaded through the Media Browser
- Double-clicking a media file adds it to the timeline with proper duration detection
- The timeline automatically creates a composite video from all clips

### 2. **Timeline-Preview Synchronization**
- **Timeline → Preview**: When you scrub the timeline, the preview updates to show the correct frame
- **Preview → Timeline**: When you scrub or play in the preview, the timeline playhead moves accordingly
- **Real-time Updates**: Adding, moving, or modifying clips immediately updates the preview

### 3. **Signal Connections**
```
Timeline.time_changed → Preview.seek_to_time()
Preview.time_changed → Timeline.set_playhead_time()
MediaBrowser.media_double_clicked → add_to_timeline() → update_composition()
Timeline.clip_moved → update_composition()
```

## Usage Instructions

### Adding Media to Timeline
1. **Load Media**: Media files are automatically loaded from your Videos folder
2. **Preview Individual Files**: Single-click a file in the media browser to preview it
3. **Add to Timeline**: Double-click a file to add it to the timeline at the current playhead position

### Timeline Operations
- **Scrub Timeline**: Click and drag on the timeline ruler to seek to different times
- **Move Clips**: Use the Select tool (V) to drag clips to different positions
- **Split Clips**: Use the Razor tool (C) to cut clips at specific points
- **Zoom**: Use the zoom slider to change timeline zoom level

### Preview Controls
- **Play/Pause**: Click the play button or press spacebar
- **Frame Navigation**: Use previous/next frame buttons
- **Timeline Scrubbing**: Drag the timeline scrubber to navigate
- **Quality Settings**: Change preview quality (25%, 50%, 100%)

### Keyboard Shortcuts
- **V**: Select tool
- **C**: Razor tool  
- **S**: Split at playhead
- **Delete**: Remove selected clips
- **Ctrl+C**: Copy clips
- **Ctrl+V**: Paste clips

## Technical Details

### Video Composition
The system creates a MoviePy `CompositeVideoClip` from all timeline clips:
- Each clip is loaded with its proper start time and duration
- Clips are composited together to create the final timeline video
- The preview widget receives this composite for playback

### Performance Optimizations
- **Frame Caching**: The preview widget caches frames for smooth playback
- **Quality Scaling**: Lower quality preview options for better performance
- **Lazy Loading**: Videos are only loaded when needed

### File Management
- Timeline clips are mapped to their source files via `timeline_clips` dictionary
- Original file paths are preserved for proper video loading
- Clips maintain their properties (duration, start time, track assignment)

## Troubleshooting

### Common Issues
1. **"No module named moviepy.editor"**: Install MoviePy with `pip install moviepy`
2. **Preview shows "No Video Loaded"**: Make sure to double-click files to add them to timeline
3. **Timeline not updating**: Check that signal connections are properly established

### Debugging
Run the integration test to verify everything is connected:
```bash
python test_integration.py
```

### Performance Tips
- Use lower preview quality (25% or 50%) for smoother playback
- Keep timeline zoom at appropriate levels
- Close unused video clips to free memory

## Future Enhancements
- Multi-track audio/video composition
- Real-time effects preview
- Transition previews
- Keyframe animation integration
- Export directly from timeline composition
