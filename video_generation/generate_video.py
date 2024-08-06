import subprocess
import math
import argparse
import os

def main():
    
    parser = argparse.ArgumentParser(description='Generating a video')
    parser.add_argument('--audio', type=str, help='Path to the audio file', required=True)
    # argument for the album cover image
    parser.add_argument('--cover_image', type=str, help='Path to the cover image', required=True)
    # argument for video duration
    parser.add_argument('--duration', type=int, help='Duration of the video in seconds', required=True)
    # argument for the output file
    parser.add_argument('--output', type=str, help='Path to the output file', required=True)
    # argument for the output size, default is 1024x1024, not required
    parser.add_argument('--output_size', type=str, help='Output size of the video', default='1024x1024')
    # argument for the blur background image, required
    parser.add_argument('--background', type=str, help='Path to the background image', required=True)

    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Configurable variables
    AUDIO_PATH = args.audio
    DURATION = args.duration
    FPS = 30
    TOTAL_FRAMES = DURATION * FPS
    OUTPUT_SIZE = args.output_size
    VINYL_IMAGE = os.path.join(script_dir, "vinylDisc.png")
    ALBUM_COVER = args.cover_image
    BACKGROUND_IMAGE = args.background
    APP_DOWNLOAD_IMAGE = os.path.join(script_dir, "app_download.png")
    VOX_LOGO_IMAGE = os.path.join(script_dir, "voxLogoRounded.png")
    TEXT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    # Calculate the ratio based on the output size
    OUTPUT_WIDTH, OUTPUT_HEIGHT = map(int, OUTPUT_SIZE.split('x'))
    TOP_PADDING = 5
    PADDED_HEIGHT_PERCENTAGE = 0.20
    PADDED_HEIGHT_VALUE = int(OUTPUT_HEIGHT * PADDED_HEIGHT_PERCENTAGE)
    PADDED_HEIGHT = OUTPUT_HEIGHT + PADDED_HEIGHT_VALUE
    RATIO = OUTPUT_WIDTH // OUTPUT_HEIGHT

    APP_DOWNLOAD_HEIGHT = int(PADDED_HEIGHT_VALUE * 0.45)
    APP_DOWNLOAD_POSITION_Y = 0

    VOX_LOGO_IMAGE_HEIGHT = int(PADDED_HEIGHT_VALUE * 0.40)
    VOX_LOGO_IMAGE_POSITION_X = int(OUTPUT_WIDTH * 0.35)
    VOX_LOGO_IMAGE_POSITION_Y = int(PADDED_HEIGHT - VOX_LOGO_IMAGE_HEIGHT - (PADDED_HEIGHT_VALUE / 2 * 0.12))

    MADE_WITH_TEXT_POSITION_Y = int(VOX_LOGO_IMAGE_POSITION_Y + ((VOX_LOGO_IMAGE_HEIGHT / 2) * 0.75))
    MADE_WITH_TEXT_POSITION_X = int(VOX_LOGO_IMAGE_POSITION_X + VOX_LOGO_IMAGE_HEIGHT + 10)
    MADE_WITH_TEXT_FONT_SIZE = int(OUTPUT_HEIGHT * 0.030)
    MADE_WITH_TEXT_COLOR = "white"

    # Calculate sizes and positions based on output dimensions
    ALBUM_COVER_SIZE = int(OUTPUT_HEIGHT * 0.50)
    ALBUM_POSITION_X = (OUTPUT_WIDTH - ALBUM_COVER_SIZE) // 2
    ALBUM_POSITION_Y = (OUTPUT_HEIGHT - ALBUM_COVER_SIZE) // 2

    VINYL_SIZE = ALBUM_COVER_SIZE
    VINYL_POSITION_X = int(ALBUM_POSITION_X + ALBUM_COVER_SIZE * 0.46)
    VINYL_POSITION_Y = (OUTPUT_HEIGHT - VINYL_SIZE) // 2

    PROGRESS_BAR_WIDTH = int(OUTPUT_WIDTH * 0.75)
    PROGRESS_BAR_HEIGHT = int(OUTPUT_HEIGHT * 0.01)
    PROGRESS_BAR_SIZE = f"{PROGRESS_BAR_WIDTH}x{PROGRESS_BAR_HEIGHT}"
    PROGRESS_BAR_POSITION_X = (OUTPUT_WIDTH - PROGRESS_BAR_WIDTH) // 2
    PROGRESS_BAR_POSITION_Y = int(OUTPUT_HEIGHT * 0.90)
    PROGRESS_BAR_BG_COLOR = "0x333333"
    PROGRESS_BAR_FG_COLOR = "0x00FF00"

    DURATION_TEXT_COLOR = "white"
    DURATION_TEXT_FONT_SIZE = int(OUTPUT_HEIGHT * 0.020)
    ELAPSED_TEXT_POSITION_Y = PROGRESS_BAR_POSITION_Y + PROGRESS_BAR_HEIGHT + 10
    REMAINING_TEXT_POSITION_X = PROGRESS_BAR_POSITION_X + PROGRESS_BAR_WIDTH - 65

    ROTATION_SPEED = 1

    OUTPUT_FILE = args.output

    ffmpeg_command = [
        "ffmpeg",
        "-loop", "1", "-i", BACKGROUND_IMAGE,
        "-loop", "1", "-i", VINYL_IMAGE,
        "-loop", "1", "-i", ALBUM_COVER,
        "-loop", "1", "-i", APP_DOWNLOAD_IMAGE,
        "-loop", "1", "-i", VOX_LOGO_IMAGE,
        "-i", AUDIO_PATH,
        "-filter_complex",
        f"""
        [0]scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},setsar=1[bg];
        [1]scale={VINYL_SIZE}:{VINYL_SIZE},rotate=angle='t*{ROTATION_SPEED}':fillcolor=none[rotating];
        [bg][rotating]overlay=x={VINYL_POSITION_X}:y={VINYL_POSITION_Y}[bg_with_rotating];
        [2]scale={ALBUM_COVER_SIZE}:-1[ovrl];
        [bg_with_rotating][ovrl]overlay=x={ALBUM_POSITION_X}:y={ALBUM_POSITION_Y}[with_cover];
        [3]scale=-1:{APP_DOWNLOAD_HEIGHT}[app_download];
        [4]scale=-1:{VOX_LOGO_IMAGE_HEIGHT}[vox_logo];
        color={PROGRESS_BAR_BG_COLOR}:s={PROGRESS_BAR_SIZE}:r=30,trim=duration={DURATION}[bg_bar];
        color={PROGRESS_BAR_FG_COLOR}:s={PROGRESS_BAR_SIZE}:r=30,
        geq='r=if(lte(X,min((T/({DURATION}-0.1))*W,W)),255,0):g=if(lte(X,min((T/({DURATION}-0.1))*W,W)),255,0):b=if(lte(X,min((T/({DURATION}-0.1))*W,W)),255,0):a=255',
        trim=duration={DURATION}[fg_bar];
        [bg_bar][fg_bar]overlay=0:0[progress_bar];
        [with_cover][progress_bar]overlay={PROGRESS_BAR_POSITION_X}:{PROGRESS_BAR_POSITION_Y}[with_progress];
        [with_progress]drawtext=fontsize={DURATION_TEXT_FONT_SIZE}:fontcolor={DURATION_TEXT_COLOR}:x={PROGRESS_BAR_POSITION_X}:y={ELAPSED_TEXT_POSITION_Y}:text='%{{eif\\:trunc(mod(t\\,3600)/60)\\:d\\:2}}\\:%{{eif\\:trunc(mod(t+1\\,60))\\:d\\:2}}':boxborderw=5,
        drawtext=fontsize={DURATION_TEXT_FONT_SIZE}:fontcolor={DURATION_TEXT_COLOR}:x={REMAINING_TEXT_POSITION_X}:y={ELAPSED_TEXT_POSITION_Y}:text='-\\%{{eif\\:trunc(({DURATION}-t)/60)\\:d\\:2}}\\:\\%{{eif\\:trunc(mod({DURATION}-t\\,60))\\:d\\:2}}':boxborderw=5,
        setpts='if(gte(T,{DURATION}-0.01),PTS+0.01/TB,PTS)',
        pad=width={OUTPUT_WIDTH}:height={PADDED_HEIGHT}:x=0:y=(oh-ih)/2:color=black[padded];
        [padded][app_download]overlay=(main_w-overlay_w)/2:{TOP_PADDING}[with_app_download];
        [with_app_download][vox_logo]overlay={VOX_LOGO_IMAGE_POSITION_X}:{VOX_LOGO_IMAGE_POSITION_Y}[with_vox_logo];
        [with_vox_logo]drawtext=fontsize={MADE_WITH_TEXT_FONT_SIZE}:fontcolor={MADE_WITH_TEXT_COLOR}:x={MADE_WITH_TEXT_POSITION_X}:y={MADE_WITH_TEXT_POSITION_Y}:text='Made with VOX AI':boxborderw=5
        [output]
        """,
        "-map", "[output]", "-map", "5:a", "-t", str(DURATION), "-c:v", "h264_nvenc", "-shortest", "-pix_fmt", "yuv420p", OUTPUT_FILE
    ]
    # Run the FFmpeg command synchronously
    return subprocess.run(ffmpeg_command, check=True)
    
if __name__ == "__main__":
    main()