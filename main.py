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
from fileUpload import upload_file, BucketType

# APPLIO_AUDIO_OUTPUT_PATH="/Users/rajan.balana/Developer/dream/Applio/assets/audios/"
APPLIO_ROOT_PATH="/workspace/Applio/"
APPLIO_ASSETS_DIR="assets/"
APPLIO_AUDIO_DIR="audios/"
APPLIO_DATASETS_DIR="datasets/"
APPLIO_LOGS_DIR="logs/"
APPLIO_LOGS_PATH= APPLIO_ROOT_PATH + APPLIO_LOGS_DIR
APPLIO_ASSETS_PATH= APPLIO_ROOT_PATH + APPLIO_ASSETS_DIR
APPLIO_AUDIO_OUTPUT_PATH= APPLIO_ASSETS_PATH + APPLIO_AUDIO_DIR
APPLIO_DATASET_OUTPUT_PATH= APPLIO_ASSETS_PATH + APPLIO_DATASETS_DIR

print("Starting the FastAPI server...")
separator = Separator(output_dir=APPLIO_AUDIO_OUTPUT_PATH, vr_params= { "batch_size": 1,"window_size": 512,"aggression": 5,"enable_tta": False,"enable_post_process": False,"post_process_threshold": 0.2,"high_end_process": False })
separator.load_model("9_HP2-UVR.pth")
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

@app.post("/download_audio_file")
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
   
# download a dataset zip file from the url and extract it to APPLIO_DATASET_OUTPUT_PATH
@app.post("/download_dataset")
async def download_dataset(input_url: str):
   # download file from url
   response = requests.get(input_url, stream=True)
   # get file name from url
   filename = input_url.split('/')[-1]
   filename_without_ext = filename.split('.')[0]
   # save the file
   with open(APPLIO_DATASET_OUTPUT_PATH + filename, 'wb') as f:
      shutil.copyfileobj(response.raw, f)
   # extract the zip file
   shutil.unpack_archive(APPLIO_DATASET_OUTPUT_PATH + filename, APPLIO_DATASET_OUTPUT_PATH + filename_without_ext)
   # delete the zip file
   os.remove(APPLIO_DATASET_OUTPUT_PATH + filename)
   return {
      "dataset_path": APPLIO_DATASET_OUTPUT_PATH + filename_without_ext,
      "short_dataset_path": APPLIO_ASSETS_DIR + APPLIO_DATASETS_DIR + filename_without_ext
   }

# get the audio file path and separate the audio and save into same folder with suffix _separated
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
         res = await download_audio(video_or_audio_url)
         file_path = res["file_path"]
         print("Audio downloaded successfully. Saved in:", file_path)
      # if ends with mp3, download the audio
      elif video_or_audio_url.endswith(".mp3") or video_or_audio_url.endswith(".wav"):
         print("Downloading the audio from the URL..., URL:", video_or_audio_url)
         res = await download_audio_file(video_or_audio_url)
         file_path = res["file_path"]
         print("Audio downloaded successfully. Saved in:", file_path)
         
   outputs = separator.separate(file_path)

   print("Audio separated successfully.", outputs)

   return {
      "vocal_file_path": APPLIO_AUDIO_OUTPUT_PATH + outputs[1],
      "instrumental_file_path":  APPLIO_AUDIO_OUTPUT_PATH + outputs[0],
      "original_file_path": file_path,
   }
   
@app.post("/merge_audio")
async def merge_audio(request_body: dict):
   print("Merging the audio...")
   vocal_file_path = request_body.get("vocal_file_path")
   instrumental_file_path = request_body.get("instrumental_file_path")
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

# get index file path and model file path and name for model id 
@app.get("/get_model_files")
async def get_model_files(model_id: str):
   # find file that contains the model_id and ends with .pth in the APPLIO_LOGS_PATH
   model_file_path = None
   model_name = None
   index_file_path = None
   index_file_name = None

   for file in os.listdir(APPLIO_LOGS_PATH):
      if model_id in file and file.endswith(".pth"):
         model_file_path = os.path.join(APPLIO_LOGS_DIR, file)
         model_name = file
         break

   # Find the folder named as model id in APPLIO_LOGS_PATH
   for folder in os.listdir(APPLIO_LOGS_PATH):
      if os.path.isdir(os.path.join(APPLIO_LOGS_PATH, folder)) and model_id in folder:
         # Find the file that starts with "added" and ends with .index inside the folder
         for file in os.listdir(os.path.join(APPLIO_LOGS_PATH, folder)):
            if (file.startswith("added") or model_id in file) and file.endswith(".index"):
               index_file_path = os.path.join(APPLIO_LOGS_DIR, folder, file)
               index_file_name = file
            elif model_file_path is None and model_name is None and model_id in file and file.endswith(".pth"):
               model_file_path = os.path.join(APPLIO_LOGS_DIR, folder, file)
               model_name = file

   return {
      "model_file_path": model_file_path,
      "model_file_name": model_name,
      "index_file_path": index_file_path,
      "index_file_name": index_file_name
   }
   
# write an API that would take a list of file paths and remove them for cleanup
@app.post("/cleanup_files")
async def cleanup_files(request_body: dict):
   file_paths = request_body.get("file_paths")
   for file_path in file_paths:
      updated_file_path = file_path
      
      if APPLIO_ROOT_PATH not in file_path:
         updated_file_path = APPLIO_ROOT_PATH + file_path
      
      try:
          os.remove(updated_file_path)
      except Exception as e:
          print("An error occurred while removing the file:", e)
          continue
   return {
      "message": "Files removed successfully."
   }

# write an API that would rename the index file 
@app.post("/rename_index_file")
async def rename_index_file(request_body: dict):
   model_id = request_body.get("model_id")
   model_info = await get_model_files(model_id)
   index_file_path = model_info["index_file_path"]
   model_file_path = model_info["model_file_path"]
   model_name = model_info["model_file_name"]
   index_file_name = model_info["index_file_name"]
   full_index_file_path = APPLIO_ROOT_PATH + index_file_path
   new_index_file_name = request_body.get("new_index_file_name")
   new_index_file_path = os.path.join(os.path.dirname(full_index_file_path), new_index_file_name)
   os.rename(full_index_file_path, new_index_file_path)
   short_new_index_file_path = new_index_file_path.split(APPLIO_ROOT_PATH)[1]
   return {
      "model_file_path": model_file_path,
      "model_file_name": model_name,
      "index_file_path": short_new_index_file_path,
      "index_file_name": new_index_file_name
   }

# upload model and index files to the R2 server
@app.post("/upload_model_files")
async def upload_model_files(request_body: dict):
   model_file_path = request_body.get("model_file_path")
   index_file_path = request_body.get("index_file_path")
   model_file_name = request_body.get("model_file_name")
   index_file_name = request_body.get("index_file_name")

   # upload model file
   print("Uploading model file...")
   full_model_file_path = APPLIO_ROOT_PATH + model_file_path
   upload_file(full_model_file_path, model_file_name, BucketType.PTH_FILES)

   # upload index file
   print("Uploading index file...")
   full_index_file_path = APPLIO_ROOT_PATH + index_file_path
   upload_file(full_index_file_path, index_file_name, BucketType.INDEX_FILES)

   return {
      "message": "Model and index files uploaded successfully."
   }
