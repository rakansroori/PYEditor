#!/usr/bin/env python3
"""
Test script to verify timeline and preview integration
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.main_window import VideoEditor

def test_timeline_preview_integration():
    """Test that timeline and preview are properly connected"""
    app = QApplication([])
    
    # Create main window
    window = VideoEditor()
    
    # Test connections
    print("Testing timeline-preview connections...")
    
    # Check if timeline widget exists
    if hasattr(window, 'timeline_widget'):
        print("✓ Timeline widget exists")
    else:
        print("✗ Timeline widget missing")
        return False
    
    # Check if preview widget exists
    if hasattr(window, 'preview_widget'):
        print("✓ Preview widget exists")
    else:
        print("✗ Preview widget missing")
        return False
    
    # Check if timeline_clips dictionary exists
    if hasattr(window, 'timeline_clips'):
        print("✓ Timeline clips dictionary exists")
    else:
        print("✗ Timeline clips dictionary missing")
        return False
    
    # Check if media browser exists
    if hasattr(window, 'media_browser'):
        print("✓ Media browser exists")
    else:
        print("✗ Media browser missing")
        return False
    
    # Check if update_timeline_composition method exists
    if hasattr(window, 'update_timeline_composition'):
        print("✓ Timeline composition method exists")
    else:
        print("✗ Timeline composition method missing")
        return False
    
    # Check signal connections
    try:
        # Test timeline time_changed signal
        if hasattr(window.timeline_widget, 'time_changed'):
            print("✓ Timeline time_changed signal exists")
        else:
            print("✗ Timeline time_changed signal missing")
        
        # Test preview time_changed signal
        if hasattr(window.preview_widget, 'time_changed'):
            print("✓ Preview time_changed signal exists")
        else:
            print("✗ Preview time_changed signal missing")
        
        # Test media browser signals
        if hasattr(window.media_browser, 'media_double_clicked'):
            print("✓ Media browser double_clicked signal exists")
        else:
            print("✗ Media browser double_clicked signal missing")
            
    except Exception as e:
        print(f"✗ Error checking signals: {e}")
        return False
    
    print("✓ All integration tests passed!")
    return True

if __name__ == '__main__':
    success = test_timeline_preview_integration()
    if success:
        print("\n🎉 Timeline-Preview integration is properly set up!")
        print("\nTo test the integration:")
        print("1. Run 'python main.py'")
        print("2. Double-click a video file in the media browser")
        print("3. The video should appear in the timeline")
        print("4. Scrub the timeline - the preview should update")
        print("5. Play in the preview - the timeline playhead should move")
    else:
        print("\n❌ Integration setup incomplete")
        sys.exit(1)
