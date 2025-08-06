# In utils.py

from moviepy.editor import VideoFileClip

def export_video(clip, output_path, codec="libx264", audio_codec="aac"):
    """
    Exports a MoviePy video clip to a file.

    Args:
        clip (moviepy.editor.VideoClip): The video clip to export.
        output_path (str): The path and filename to save the video to (e.g., "output/final_video.mp4").
        codec (str): The video codec to use. 'libx264' is standard for .mp4 files.
        audio_codec (str): The audio codec to use. 'aac' is standard for .mp4 files.
    """
    try:
        print(f"Starting video export to {output_path}...")
        clip.write_videofile(
            output_path,
            codec=codec,
            audio_codec=audio_codec,
            temp_audiofile='temp-audio.m4a', # Recommended for compatibility
            remove_temp=True
        )
        print(f"Video successfully exported to {output_path}")
    except Exception as e:
        print(f"An error occurred during video export: {e}")
