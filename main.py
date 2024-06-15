from typing import Union

from fastapi import FastAPI
import json
import time
import requests
import os
from urllib.parse import unquote
import random
from audio_separator.separator import Separator
from pydub import AudioSegment
import shutil

APPLIO_AUDIO_OUTPUT_PATH="/Users/rajan.balana/Developer/dream/Applio/assets/audios/" # workspace/Applio/assets/audios/

print("Starting the FastAPI server...")
separator = Separator(output_dir=APPLIO_AUDIO_OUTPUT_PATH, vr_params= { "batch_size": 1,"window_size": 512,"aggression": 5,"enable_tta": False,"enable_post_process": False,"post_process_threshold": 0.2,"high_end_process": False })
# separator.load_model("9_HP2-UVR.pth")
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/download_audio")
async def download_audio(input_url: str):
   api_url = "https://co.wuk.sh/api/json"  # Update the URL if necessary

   # Define the request body as a Python dictionary
   request_body = {
      "url": input_url,              # Replace with the actual URL of the video
      "vCodec": "h264",              # Video codec (h264, av1, vp9)
      "vQuality": "720",             # Video quality (e.g., 720)
      "aFormat": "wav",              # Audio format (mp3, ogg, wav, opus)
      "isAudioOnly": True,           # Set to True to extract audio only
      "isAudioMuted": False,         # Set to True to disable audio in video
   }

   # Convert the request body dictionary to JSON
   request_body_json = json.dumps(request_body)

   # Set the headers including the "Accept" header
   headers = {
      "Content-Type": "application/json",  # Specify the content type as JSON
      "Accept": "application/json"         # Specify that you accept JSON responses
   }

   # Number of retries
   max_retries = 5

   # Initialize response variable
   response = None
   filename = None
   newPath = None

   # Retry loop
   for attempt in range(max_retries):
      try:
         # Send the POST request to the API with headers
         response = requests.post(api_url, data=request_body_json, headers=headers)

         # If the response status code is 200, break out of the loop
         if response.status_code == 200:
            print(f"Audio download request succeeded.")
            break
         else:
            print(f"Received 400 response, retrying... (Attempt {attempt + 1}/{max_retries})")

         # Wait for 1 second before retrying
         time.sleep(1)
      except Exception as e:
         print("An error occurred:", e)
         break

   # Check if the request was successful (status code 200)
   if response and response.status_code == 200:
      # Parse the response JSON
      response_data = response.json()

      # Check the status of the response
      if response_data["status"] == "stream":
         # Extract the audio URL from the response
         audio_url = response_data["url"]

         # Download the audio using wget
         print("Downloading audio...")
         filename = ""

         responseAudio = requests.get(audio_url, stream=True)
         if response.status_code == 200:
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
               filename = unquote(content_disposition.split('filename=')[1].strip('"'))
            else:
               # need a temp random filename
               filename = f"audio_{random.randint(1000, 9999)}.wav"

            newPath = os.path.join(APPLIO_AUDIO_OUTPUT_PATH, filename)
            print("Downloading audio to:", newPath)
            os.makedirs(os.path.dirname(newPath), exist_ok=True)

            with open(newPath, 'wb') as f:
               for chunk in responseAudio.iter_content(1024):
                  f.write(chunk)

            print(f"Audio downloaded successfully. Saved as: {newPath}")
         else:
            raise Exception("Failed to download audio after several attempts.")

      else:
         print("API request succeeded, but status is not 'stream'. Status:", response_data["status"])
   else:
      print("Failed to download audio after several attempts.")

   return {
      "file_path": newPath
   }

   if filename is None:
      raise Exception("Failed to download audio.")


async def download_audio_file(input_url: str):
   # download file from url
   response = requests.get(input_url, stream=True)
   # get file name from url
   filename = input_url.split('/')[-1]
   # save the file
   with open(APPLIO_AUDIO_OUTPUT_PATH + filename, 'wb') as f:
      shutil.copyfileobj(response.raw, f)
   return {
      "file_path": APPLIO_AUDIO_OUTPUT_PATH + filename
   }

# get the audio file path and separate the audio and save into same folder with suffix _seperated
@app.post("/separate_audio")
async def separate_audio(request_body: dict):
   print("Separating the audio...")
   print("Loading the audio separator...")
   file_path = request_body.get("file_path")
   video_or_audio_url = request_body.get("video_or_audio_url")
   
   if file_path: 
      print("Reading the audio file...")
   elif video_or_audio_url: 
      # detect if file is a youtube URL 
      if "youtube.com" in video_or_audio_url or "youtu.be" in video_or_audio_url:
         print("Downloading the audio from youtube..., URL:", video_or_audio_url)
         file_path = await download_audio(video_or_audio_url)
         print("Audio downloaded successfully. Saved in:", file_path)
      # if ends with mp3, download the audio
      elif video_or_audio_url.endswith(".mp3"):
         print("Downloading the audio from the URL..., URL:", video_or_audio_url)
         file_path = await download_audio_file(video_or_audio_url)
         print("Audio downloaded successfully. Saved in:", file_path)
         
   outputs = separator.separate(file_path)

   print("Audio separated successfully.", outputs)

   return {
      "vocal_file_path": APPLIO_AUDIO_OUTPUT_PATH + outputs[1],
      "instrumental_file_path":  APPLIO_AUDIO_OUTPUT_PATH + outputs[0],
      "original_file_path": file_path,
   }
   
@app.post("/merge_audio")
async def merge_audio(vocal_file_path: str, instrumental_file_path: str):
   print("Merging the audio...")
   vocal_audio = AudioSegment.from_wav(vocal_file_path)
   instrumental_audio = AudioSegment.from_wav(instrumental_file_path)

   # Ensure that the audio files have the same duration
   min_duration = min(len(vocal_audio), len(instrumental_audio))
   vocal_audio = vocal_audio[:min_duration]
   instrumental_audio = instrumental_audio[:min_duration]

   # Combine the audio files
   merged_audio = vocal_audio.overlay(instrumental_audio)

   vocal_file_name = vocal_file_path.split('/')[-1].split('.')[0]

   # Save the merged audio
   merged_audio_path = f'{APPLIO_AUDIO_OUTPUT_PATH}{vocal_file_name}_merged.wav'
   merged_audio.export(merged_audio_path, format="wav")

   print("Audio merged successfully.")

   return {
      "merged_audio_path": merged_audio_path
   }



