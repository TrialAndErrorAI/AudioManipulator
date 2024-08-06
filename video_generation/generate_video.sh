#!/bin/bash

# create a blur image background from the cover image
magick albumcover.jpg -scale 10% -blur 0x6 -scale 100% blur_albumcover.jpg

# Configurable variables
AUDIO_PATH="audio_4181.wav"
DURATION=10
FPS=30
TOTAL_FRAMES=$(echo "$DURATION * $FPS" | bc)
BACKGROUND_COLOR="0x003655"
OUTPUT_SIZE="1024x1024"
VINYL_IMAGE="vinylDisc.png"
ALBUM_COVER="albumcover.jpg"
BACKGROUND_IMAGE="blur_albumcover.jpg"
APP_DOWNLOAD_IMAGE="app_download.png"
VOX_LOGO_IMAGE="voxLogoRounded.png"

# Calculate the ratio based on the output size
OUTPUT_WIDTH=$(echo $OUTPUT_SIZE | cut -d 'x' -f 1)
OUTPUT_HEIGHT=$(echo $OUTPUT_SIZE | cut -d 'x' -f 2)
TOP_PADDING=5
PADDED_HEIGHT_PERCENTAGE=0.20
PADDED_HEIGHT_VALUE=$(echo "scale=0; $OUTPUT_HEIGHT * $PADDED_HEIGHT_PERCENTAGE / 1" | bc)
PADDED_HEIGHT=$(echo "scale=0; $OUTPUT_HEIGHT + $PADDED_HEIGHT_VALUE" | bc)
RATIO=$(echo "scale=0; $OUTPUT_WIDTH / $OUTPUT_HEIGHT" | bc)

APP_DOWNLOAD_HEIGHT=$(echo "scale=0; $PADDED_HEIGHT_VALUE * 0.45 / 1" | bc)  # 75% of the padded height
APP_DOWNLOAD_POSITION_Y=0  # 10 pixels from the top

VOX_LOGO_IMAGE_HEIGHT=$(echo "scale=0; $PADDED_HEIGHT_VALUE * 0.40 / 1" | bc)  # 75% of the padded height
VOX_LOGO_IMAGE_POSITION_X=$(echo "scale=0; $OUTPUT_WIDTH * 0.35 / 1" | bc)  # 85% of the output width
VOX_LOGO_IMAGE_POSITION_Y=$(echo "scale=0; $PADDED_HEIGHT - $VOX_LOGO_IMAGE_HEIGHT - ($PADDED_HEIGHT_VALUE / 2 * 0.12) / 1" | bc)  # 5% from the bottom

MADE_WITH_TEXT_POSITION_Y=$(echo "scale=0; $VOX_LOGO_IMAGE_POSITION_Y + (($VOX_LOGO_IMAGE_HEIGHT / 2) * 0.75) / 1" | bc)
MADE_WITH_TEXT_POSITION_X=$(echo "scale=0; $VOX_LOGO_IMAGE_POSITION_X + $VOX_LOGO_IMAGE_HEIGHT + 10" | bc)
MADE_WITH_TEXT_FONT_SIZE=$(echo "scale=0; $OUTPUT_HEIGHT * 0.030 / 1" | bc)
MADE_WITH_TEXT_COLOR="white"

# Calculate sizes and positions based on output dimensions
ALBUM_COVER_SIZE=$(echo "scale=0; $OUTPUT_HEIGHT * 0.50 / 1" | bc)  # 500/720 ≈ 0.694444
ALBUM_POSITION_X=$(echo "scale=0; ($OUTPUT_WIDTH - $ALBUM_COVER_SIZE) / 2 / 1" | bc)
ALBUM_POSITION_Y=$(echo "scale=0; ($OUTPUT_HEIGHT - $ALBUM_COVER_SIZE) / 2 / 1" | bc)

VINYL_SIZE=$ALBUM_COVER_SIZE
VINYL_POSITION_X=$(echo "scale=0; $ALBUM_POSITION_X + $ALBUM_COVER_SIZE * 0.46 / 1" | bc)
VINYL_POSITION_Y=$(echo "scale=0; ($OUTPUT_HEIGHT - $VINYL_SIZE) / 2 / 1" | bc)

PROGRESS_BAR_WIDTH=$(echo "scale=0; $OUTPUT_WIDTH * 0.75 / 1" | bc)  # 980/1280 ≈ 0.765625
PROGRESS_BAR_HEIGHT=$(echo "scale=0; $OUTPUT_HEIGHT * 0.01 / 1" | bc)  # 10/720 ≈ 0.013888
PROGRESS_BAR_SIZE="${PROGRESS_BAR_WIDTH}x${PROGRESS_BAR_HEIGHT}"
PROGRESS_BAR_POSITION_X=$(echo "scale=0; ($OUTPUT_WIDTH - $PROGRESS_BAR_WIDTH) / 2 / 1" | bc)
PROGRESS_BAR_POSITION_Y=$(echo "scale=0; $OUTPUT_HEIGHT * 0.90 / 1" | bc)
PROGRESS_BAR_BG_COLOR="0x333333"
PROGRESS_BAR_FG_COLOR="0x00FF00"

DURATION_TEXT_FONT="Arial"
DURATION_TEXT_COLOR="white"
DURATION_TEXT_FONT_SIZE=$(echo "scale=0; $OUTPUT_HEIGHT * 0.020 / 1" | bc)  # Adjust as needed
ELAPSED_TEXT_POSITION_Y=$(echo "scale=0; $PROGRESS_BAR_POSITION_Y + $PROGRESS_BAR_HEIGHT + 10" | bc)
REMAINING_TEXT_POSITION_X=$(echo "scale=0; $PROGRESS_BAR_POSITION_X + $PROGRESS_BAR_WIDTH - 47" | bc)

ROTATION_SPEED=1

OUTPUT_FILE="output.mp4"

# FFmpeg command
ffmpeg -loop 1 -i ${BACKGROUND_IMAGE} \
  -loop 1 -i ${VINYL_IMAGE} \
  -loop 1 -i ${ALBUM_COVER} \
  -loop 1 -i ${APP_DOWNLOAD_IMAGE} \
  -loop 1 -i ${VOX_LOGO_IMAGE} \
  -i "${AUDIO_PATH}" \
  -filter_complex "
    [0]scale=${OUTPUT_WIDTH}:${OUTPUT_HEIGHT},setsar=1[bg];
    [1]scale=${VINYL_SIZE}:${VINYL_SIZE},rotate=angle='t*${ROTATION_SPEED}':fillcolor=none[rotating];
    [bg][rotating]overlay=x=${VINYL_POSITION_X}:y=${VINYL_POSITION_Y}[bg_with_rotating];
    [2]scale=${ALBUM_COVER_SIZE}:-1[ovrl];
    [bg_with_rotating][ovrl]overlay=x=${ALBUM_POSITION_X}:y=${ALBUM_POSITION_Y}[with_cover];
    [3]scale=-1:${APP_DOWNLOAD_HEIGHT}[app_download];
    [4]scale=-1:${VOX_LOGO_IMAGE_HEIGHT}[vox_logo];
    color=${PROGRESS_BAR_BG_COLOR}:s=${PROGRESS_BAR_SIZE}:r=30,trim=duration=${DURATION}[bg_bar];
    color=${PROGRESS_BAR_FG_COLOR}:s=${PROGRESS_BAR_SIZE}:r=30,
    geq='r=if(lte(X,min((T/(${DURATION}-0.1))*W,W)),255,0):g=if(lte(X,min((T/(${DURATION}-0.1))*W,W)),255,0):b=if(lte(X,min((T/(${DURATION}-0.1))*W,W)),255,0):a=255',
    trim=duration=${DURATION}[fg_bar];
    [bg_bar][fg_bar]overlay=0:0[progress_bar];
    [with_cover][progress_bar]overlay=${PROGRESS_BAR_POSITION_X}:${PROGRESS_BAR_POSITION_Y}[with_progress];
    [with_progress]drawtext=fontsize=${DURATION_TEXT_FONT_SIZE}:fontcolor=${DURATION_TEXT_COLOR}:x=${PROGRESS_BAR_POSITION_X}:y=${ELAPSED_TEXT_POSITION_Y}:text='%{eif\:trunc(mod(t\,3600)/60)\:d\:2}\:%{eif\:trunc(mod(t+1\,60))\:d\:2}':boxborderw=5,
    drawtext=fontsize=${DURATION_TEXT_FONT_SIZE}:fontcolor=${DURATION_TEXT_COLOR}:x=${REMAINING_TEXT_POSITION_X}:y=${ELAPSED_TEXT_POSITION_Y}:text='-\%{eif\:trunc((${DURATION}-t)/60)\:d\:2}\:\%{eif\:trunc(mod(${DURATION}-t\,60))\:d\:2}':boxborderw=5,
    setpts='if(gte(T,${DURATION}-0.01),PTS+0.01/TB,PTS)',
    pad=width=${OUTPUT_WIDTH}:height=${PADDED_HEIGHT}:x=0:y=(oh-ih)/2:color=black[padded];
    [padded][app_download]overlay=(main_w-overlay_w)/2:${TOP_PADDING}[with_app_download];
    [with_app_download][vox_logo]overlay=${VOX_LOGO_IMAGE_POSITION_X}:${VOX_LOGO_IMAGE_POSITION_Y}[with_vox_logo];
    [with_vox_logo]drawtext=fontsize=${MADE_WITH_TEXT_FONT_SIZE}:fontcolor=${MADE_WITH_TEXT_COLOR}:x=${MADE_WITH_TEXT_POSITION_X}:y=${MADE_WITH_TEXT_POSITION_Y}:text='Made with VOX AI':boxborderw=5
  [output]" \
  -map "[output]" -map 5:a -t ${DURATION} -c:v libx264 -shortest -pix_fmt yuv420p ${OUTPUT_FILE}