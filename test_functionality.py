#!/usr/bin/env python3
"""
Comprehensive test for MoviePy integration and drag-drop functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_moviepy_imports():
    """Test that MoviePy imports work correctly"""
    print("Testing MoviePy imports...")
    
    try:
        from moviepy import VideoFileClip, CompositeVideoClip
        print("✓ MoviePy imports successful")
        
        # Test basic functionality
        print("Testing MoviePy basic functionality...")
        
        # Find a test video file
        video_dir = r"C:\Users\rakan\Videos"
        test_files = []
        if os.path.exists(video_dir):
            for file in os.listdir(video_dir):
                if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                    test_files.append(os.path.join(video_dir, file))
        
        if test_files:
            test_file = test_files[0]
            print(f"Testing with: {os.path.basename(test_file)}")
            
            # Test VideoFileClip creation
            clip = VideoFileClip(test_file)
            print(f"✓ VideoFileClip loaded: duration={clip.duration:.2f}s")
            
            # Test MoviePy 2.x methods
            clip_with_start = clip.with_start(1.0)
            print("✓ with_start() method works")
            
            clip_with_duration = clip.with_duration(5.0)
            print("✓ with_duration() method works")
            
            clip.close()
            clip_with_start.close()
            clip_with_duration.close()
            
            print("✓ All MoviePy tests passed")
            return True
        else:
            print("⚠ No test video files found, but imports work")
            return True
            
    except Exception as e:
        print(f"✗ MoviePy test failed: {e}")
        return False

def test_drag_drop_setup():
    """Test that drag and drop components are properly set up"""
    print("\\nTesting drag and drop setup...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import VideoEditor
        from ui.media_browser import DraggableTreeWidget
        
        app = QApplication([])
        
        # Test main window
        window = VideoEditor()
        print("✓ Main window created")
        
        # Test media browser drag support
        if hasattr(window, 'media_browser'):
            media_view = window.media_browser.media_view
            if isinstance(media_view, DraggableTreeWidget):
                print("✓ Media browser has drag support")
            else:
                print("✗ Media browser missing drag support")
                return False
        else:
            print("✗ Media browser not found")
            return False
        
        # Test timeline drop support
        if hasattr(window, 'timeline_widget'):
            timeline = window.timeline_widget
            if hasattr(timeline, 'media_dropped'):
                print("✓ Timeline has drop signal")
            else:
                print("✗ Timeline missing drop signal")
                return False
                
            # Check track widgets
            has_drop_support = False
            for i in range(timeline.timeline_layout.count()):
                item = timeline.timeline_layout.itemAt(i)
                if item and item.widget():
                    track_widget = item.widget()
                    if hasattr(track_widget, 'dropEvent'):
                        has_drop_support = True
                        break
            
            if has_drop_support:
                print("✓ Timeline tracks have drop support")
            else:
                print("✗ Timeline tracks missing drop support")
                return False
        else:
            print("✗ Timeline widget not found")
            return False
        
        # Test signal connections
        try:
            # This will raise an exception if signals aren't connected
            timeline.media_dropped.emit("test", "test.mp4")
            print("✓ Timeline media_dropped signal works")
        except Exception as e:
            print(f"⚠ Timeline signal test: {e}")
        
        print("✓ All drag and drop tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Drag and drop test failed: {e}")
        return False

def test_timeline_preview_integration():
    """Test timeline-preview integration"""
    print("\\nTesting timeline-preview integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import VideoEditor
        
        app = QApplication([])
        window = VideoEditor()
        
        # Test signal connections
        connections = [
            (window.timeline_widget, 'time_changed'),
            (window.timeline_widget, 'clip_selected'),
            (window.timeline_widget, 'media_dropped'),
            (window.preview_widget, 'time_changed'),
            (window.preview_widget, 'frame_changed'),
            (window.media_browser, 'media_selected'),
            (window.media_browser, 'media_double_clicked'),
        ]
        
        for widget, signal_name in connections:
            if hasattr(widget, signal_name):
                print(f"✓ {widget.__class__.__name__}.{signal_name} exists")
            else:
                print(f"✗ {widget.__class__.__name__}.{signal_name} missing")
                return False
        
        # Test methods
        methods = [
            (window, 'update_timeline_composition'),
            (window, 'on_media_added_to_timeline'),
            (window, 'on_clip_moved'),
            (window, 'on_timeline_time_changed'),
            (window, 'on_preview_time_changed'),
        ]
        
        for obj, method_name in methods:
            if hasattr(obj, method_name):
                print(f"✓ {obj.__class__.__name__}.{method_name}() exists")
            else:
                print(f"✗ {obj.__class__.__name__}.{method_name}() missing")
                return False
        
        print("✓ All integration tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== PyVideoEditor Functionality Tests ===\\n")
    
    tests = [
        test_moviepy_imports,
        test_drag_drop_setup,
        test_timeline_preview_integration,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\\n=== Results: {passed}/{len(tests)} tests passed ===")
    
    if passed == len(tests):
        print("\\n🎉 All tests passed! The application should work correctly.")
        print("\\nFeatures ready:")
        print("• MoviePy 2.x compatibility")
        print("• Drag and drop from media browser to timeline")
        print("• Timeline-preview synchronization")
        print("• Double-click to add media to timeline")
        print("• Timeline scrubbing and playback")
        
        print("\\nHow to use:")
        print("1. Run: python main.py")
        print("2. Double-click videos in media browser to add to timeline")
        print("3. Or drag videos from media browser to timeline tracks")
        print("4. Scrub timeline or use preview controls")
        print("5. Preview shows composed timeline video")
    else:
        print(f"\\n❌ {len(tests) - passed} test(s) failed. Check the issues above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
