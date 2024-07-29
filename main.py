from typing import Union
import logging
from fastapi import FastAPI
import json
import time
import requests
import concurrent.futures
import os
from urllib.parse import unquote
import random
from audio_separator.separator import Separator
from pydub import AudioSegment
import shutil
from fileUpload import upload_file, BucketType
import asyncio
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterGRPC,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# APPLIO_ROOT_PATH="/Users/rajan.balana/Developer/dream/Applio/"
APPLIO_ROOT_PATH="/workspace/Applio/"
APPLIO_ASSETS_DIR="assets/"
APPLIO_AUDIO_DIR="audios/"
APPLIO_DATASETS_DIR="datasets/"
APPLIO_LOGS_DIR="logs/"
APPLIO_LOGS_PATH= APPLIO_ROOT_PATH + APPLIO_LOGS_DIR
APPLIO_ASSETS_PATH= APPLIO_ROOT_PATH + APPLIO_ASSETS_DIR
APPLIO_AUDIO_OUTPUT_PATH= APPLIO_ASSETS_PATH + APPLIO_AUDIO_DIR
APPLIO_DATASET_OUTPUT_PATH= APPLIO_ASSETS_PATH + APPLIO_DATASETS_DIR
SERVICE_NAME= "AudioManipulator"

# OpenTelemetry Common Setup
resource = Resource.create({"service.name": SERVICE_NAME})

# OpenTelemetry Logging Setup 

logger_provider = LoggerProvider(resource)

set_logger_provider(logger_provider)
logging.basicConfig(level=logging.INFO)

exporter = OTLPLogExporter(endpoint="grpc://174.138.34.94:4317", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

logger = logging.getLogger("AudioManipulator")
logger.addHandler(handler)

# OpenTelemetry Metrics Setup

metric_reader = PeriodicExportingMetricReader(
   OTLPMetricExporter(endpoint="http://174.138.34.94:4318/v1/metrics")
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# OpenTelemetry Traces Setup
tracer = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer)

tracer.add_span_processor(
   BatchSpanProcessor(
       OTLPSpanExporterGRPC(endpoint="grpc://174.138.34.94:4317", insecure=True)
   )
)

logger.info("Starting the FastAPI server...")
separator = Separator(output_dir=APPLIO_AUDIO_OUTPUT_PATH, vr_params= { "batch_size": 1,"window_size": 512,"aggression": 5,"enable_tta": False,"enable_post_process": False,"post_process_threshold": 0.2,"high_end_process": False })
separator.load_model("9_HP2-UVR.pth")
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
 
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Audio Manipulator is running."}

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
            logger.info("Audio download request succeeded.")
            break
         else:
            logger.warn(f"Received 400 response, retrying... (Attempt {attempt + 1}/{max_retries})")

         # Wait for 1 second before retrying
         time.sleep(1)
      except Exception as e:
         logger.error(f"An error occurred: {e}")
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
         logger.info("Downloading audio...")
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
            logger.info(f"Downloading audio to: {newPath}")
            os.makedirs(os.path.dirname(newPath), exist_ok=True)

            with open(newPath, 'wb') as f:
               for chunk in responseAudio.iter_content(1024):
                  f.write(chunk)

            logger.info(f"Audio downloaded successfully. Saved as: {newPath}")
         else:
            raise Exception("Failed to download audio after several attempts.")

      else:
         logger.warn(f"API request succeeded, but status is not 'stream'. Status: {response_data['status']}")
   else:
      logger.error("Failed to download audio after several attempts.")

   return {
      "file_path": newPath
   }

   if filename is None:
      raise Exception("Failed to download audio.")

@app.post("/download_audio_file")
async def download_file(input_url: str):
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
   start_time = time.time()  # Start the timer
   logger.info("Separating the audio...\n")
   file_path = request_body.get("file_path")
   video_or_audio_url = request_body.get("video_or_audio_url")
   audio_id = request_body.get("audio_id")
   purpose = request_body.get("purpose")
   
   if file_path: 
      logger.info("Reading the audio file...\n")
   elif video_or_audio_url: 
      # detect if file is a youtube URL 
      if "youtube.com" in video_or_audio_url or "youtu.be" in video_or_audio_url:
         logger.info(f"Downloading the audio from youtube..., URL: {video_or_audio_url}\n")
         try:
            res = await download_audio(video_or_audio_url)
            file_path = res["file_path"]
         except Exception as e:
            logger.error(f"Error occurred while downloading audio from YouTube, Video URL: {video_or_audio_url}, error: {str(e)}\n")
            return {
               "status": "error",
               "error": f"Error occurred while downloading audio: {str(e)}"
            }
         logger.info(f"Audio downloaded successfully. Saved in: {file_path}\n")
      # if ends with mp3, download the audio
      elif video_or_audio_url.endswith(".mp3") or video_or_audio_url.endswith(".wav"):
         logger.info(f"Downloading the audio from the URL... URL: {video_or_audio_url}\n")
         res = await download_file(video_or_audio_url)
         file_path = res["file_path"]
         logger.info(f"Audio downloaded successfully. Saved in: {file_path}\n")

   if file_path is None:
      logger.error(f"Audio download unsuccessful, URL: {video_or_audio_url}, audio_id: {audio_id}\n")
      return {
         "status": "error",
         "error": f"Unable to download audio, URL: {video_or_audio_url}, audio_id: {audio_id}"
      }
   
   try:
      outputs = separator.separate(file_path)
   except Exception as e:
      logger.error(f"Error occurred while separating audio: {str(e)}")
      cleanup_files({"paths": [file_path]})
      return {
         "status": "error",
         "error": f"Error occurred while separating audio: {str(e)}"
      }
   
   logger.info(f"Audio separated successfully. Outputs: {outputs}\n")
   
   instrumental_file_path =  APPLIO_AUDIO_OUTPUT_PATH + outputs[0]
   vocal_file_path =  APPLIO_AUDIO_OUTPUT_PATH + outputs[1]
   original_file_path = file_path
   
   logger.info("Uploading the audio files to R2...\n")
   
   # Create a function to upload a file
   def upload_local_file(file_path, file_name):
      file_upload_rs = upload_file(file_path, file_name, BucketType.CONTENT_FILES)
      if file_upload_rs is None:
         raise Exception(f"Failed to upload {file_name}")
      return file_upload_rs

   # Create a list of paths and file names
   upload_paths = []
   file_names = []
   if purpose is not None and purpose == "vocal_remover":
      upload_paths = [original_file_path, instrumental_file_path, vocal_file_path]
      file_names = [audio_id, f'{audio_id}_instrumental.mp3', f'{audio_id}_vocal.mp3']

   # check if there are any files to upload, if not return the response
   if len(upload_paths) == 0:
      response = {
         "status": "success",
         "vocal_file_path": vocal_file_path,
         "instrumental_file_path":  instrumental_file_path,
         "original_file_path": original_file_path,
      }
      
      logger.info(f"Audio separation response: {response}\n")
      
      return response

   # Use concurrent.futures to upload files in parallel
   with concurrent.futures.ThreadPoolExecutor() as executor:
         
      # Submit the upload tasks
      upload_tasks = [executor.submit(upload_local_file, file_path, file_name) for file_path, file_name in zip(upload_paths, file_names)]
      
      # Wait for all tasks to complete
      concurrent.futures.wait(upload_tasks)
      
      # Get the results of the upload tasks
      results = [task.result() for task in upload_tasks]
      
      # Check if any upload failed
      if None in results:
         raise Exception("Failed to upload audio files")
      
      original_file_upload_rs, instrumental_file_upload_rs, vocal_file_upload_rs = results
   
   end_time = time.time()  # Stop the timer
   elapsed_time = end_time - start_time  # Calculate the elapsed time

   logger.info(f"Time taken: {elapsed_time} seconds\n")  # Print the elapsed time
   
   response = {
      "status": "success",
      "vocal_file_path": vocal_file_path,
      "instrumental_file_path":  instrumental_file_path,
      "original_file_path": original_file_path,
      "r2_original_file_url": original_file_upload_rs,
      "r2_vocal_file_url": vocal_file_upload_rs,
      "r2_instrumental_file_url": instrumental_file_upload_rs
   }

   logger.info(f"Audio separation response: {response}\n")

   return response
   
@app.post("/merge_audio")
async def merge_audio(request_body: dict):
   logger.info("Merging the audio...")
   vocal_file_path = request_body.get("vocal_file_path")
   instrumental_file_path = request_body.get("instrumental_file_path")
   audio_id = request_body.get("audio_id")
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
   merged_audio_path = f'{APPLIO_AUDIO_OUTPUT_PATH}{vocal_file_name}_merged.mp3'
   merged_audio.export(merged_audio_path, format="mp3")

   logger.info("Audio merged successfully.")
   
   file_upload_rs = upload_file(merged_audio_path, audio_id, BucketType.CONTENT_FILES)
   
   if file_upload_rs is None:
      raise Exception("Failed to upload the merged audio file.")
   
   logger.info(f"Merged audio uploaded successfully to R2. URL: {file_upload_rs}")

   return {
      "merged_audio_path": merged_audio_path,
      "r2_merged_audio_url": file_upload_rs
   }

# get index file path and model file path and name for model id 
@app.get("/get_model_files")
async def get_model_files(model_id: str):
   logger.info(f"Getting model files for model id: {model_id}")
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
   paths = request_body.get("paths")
   for path in paths:
      updated_path = path
      
      if APPLIO_ROOT_PATH not in path:
         updated_path = APPLIO_ROOT_PATH + path
      
      try:
         if os.path.isfile(updated_path):
           os.remove(updated_path)
         elif os.path.isdir(updated_path):
           shutil.rmtree(updated_path)
      except Exception as e:
         logger.error(f"An error occurred while removing the file: {e}")
         continue
   return {
      "message": "Files removed successfully."
   }

# write an API that would rename the index file 
@app.post("/make_index_file_name_unique")
async def make_index_file_name_unique(request_body: dict):
   model_id = request_body.get("model_id")
   model_info = await get_model_files(model_id)
   index_file_path = model_info["index_file_path"]
   model_file_path = model_info["model_file_path"]
   model_name = model_info["model_file_name"]
   index_file_name = model_info["index_file_name"]
   full_index_file_path = APPLIO_ROOT_PATH + index_file_path
   new_index_file_name = index_file_name.replace(".index", f"_vox_{model_id}.index") # create a unique index file name to avoid file from being overwritten in R2       
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
   
   # Create a function to upload a file
   def upload_local_file(file_path, file_name, bucket_type: BucketType):
      file_upload_rs = upload_file(file_path, file_name, bucket_type)
      if file_upload_rs is None:
         raise Exception(f"Failed to upload {file_name}")
      return file_upload_rs

   
   logger.info("Uploading model and index files...")
   
   # Create a list of paths and file names
   upload_paths = [APPLIO_ROOT_PATH + model_file_path, APPLIO_ROOT_PATH + index_file_path]
   file_names = [model_file_name, index_file_name]
   bucket_types = [BucketType.PTH_FILES, BucketType.INDEX_FILES]

   # Use concurrent.futures to upload files in parallel
   with concurrent.futures.ThreadPoolExecutor() as executor:
      # Submit the upload tasks
      upload_tasks = [executor.submit(upload_local_file, file_path, file_name, bucket_type) for file_path, file_name, bucket_type in zip(upload_paths, file_names, bucket_types)]
      
      # Wait for all tasks to complete
      concurrent.futures.wait(upload_tasks)
      
      # Get the results of the upload tasks
      results = [task.result() for task in upload_tasks]
      
      # Check if any upload failed
      if None in results:
         raise Exception("Failed to upload model files")

   return {
      "message": "Model and index files uploaded successfully.",
   }
   
# create an endpoint that will take a list of file paths and upload them to the R2 server in parallel
@app.post("/upload_files_to_r2")
async def upload_files_to_r2(request_body: dict):
   paths = request_body.get("paths_and_file_names")
   bucket_type = request_body.get("bucket_type") or BucketType.CONTENT_FILES
   
   logger.info(f"Uploading files to R2, paths: {paths}, bucket_type: {bucket_type}")
   
   # Create a function to upload a file
   def upload_local_file(file_path, file_name):
      # check if file path already has APPLIO_ROOT_PATH
      temp_file_path = file_path
      if APPLIO_ROOT_PATH not in temp_file_path:
         temp_file_path = APPLIO_ROOT_PATH + file_path
      
      file_upload_rs = upload_file(temp_file_path, file_name, bucket_type)
      if file_upload_rs is None:
         raise Exception(f"Failed to upload {temp_file_path}")
      return {
         "file_path": file_path,
         "r2_url": file_upload_rs
      }

   # Use concurrent.futures to upload files in parallel
   with concurrent.futures.ThreadPoolExecutor() as executor:
      # Submit the upload tasks
      # paths is a dictionary with keys as file paths and values as file names
      upload_tasks = [executor.submit(upload_local_file, file_path, file_name) for file_path, file_name in paths.items()]
      
      # Wait for all tasks to complete
      concurrent.futures.wait(upload_tasks)
      
      # Get the results of the upload tasks
      results = [task.result() for task in upload_tasks]
      
      # make the results as a dictionary
      results = {result["file_path"]: result["r2_url"] for result in results}
      
      logger.info(f"Files uploaded successfully to R2, results: {results}")
      
      # Check if any upload failed
      if None in results:
         logger.error("Failed to upload files, paths: {paths}, bucket_type: {bucket_type}")
         return {
            "status": "error",
            "error": "Failed to upload files"
         }

   return {
      "status": "success",
      "uploaded_files": results
   }
   
@app.post("/generate_video")
async def generate_video(request_body: dict): 
   logger.info("Generating the video...")
   audio_url = request_body.get("audio_url")
   audio_data = request_body.get("audio_data")
   cover_image_url = request_body.get("cover_image_url")
   audio_id = request_body.get("audio_id")
   
   audio_file_path = None
   
   # download the audio if audio_url is provided
   if audio_url:
      logger.info(f"Downloading the audio from the URL... URL: {audio_url}\n")
      res = await download_file(audio_url)
      audio_file_path = res["file_path"]
      logger.info(f"Audio downloaded successfully. Saved in: {audio_file_path}\n")
   
   # check if audio_data base64 is provided and save it to a file
   if audio_data is not None and audio_data != "":
      audio_file_path = f"{APPLIO_AUDIO_OUTPUT_PATH}{audio_id}"
      with open(audio_file_path, "wb") as f:
         f.write(base64.b64decode(audio_data))
      logger.info(f"Audio data saved successfully. Saved in: {audio_file_path}\n")
   
   # download the cover image if cover_image_url is provided
   if cover_image_url:
      logger.info(f"Downloading the cover image from the URL... URL: {cover_image_url}\n")
      res = await download_file(cover_image_url)
      cover_image_path = res["file_path"]
      logger.info(f"Cover image downloaded successfully. Saved in: {cover_image_path}\n")
   else:
      # pick default cover image
      logger.info("Using the default cover image...\n")
      cover_image_path = f"{APPLIO_ROOT_PATH}default_cover_image.png"

   # create a short random string using current timestamp
   short_rand_string = str(int(time.time()))

   # create a video from the audio and cover image
   clean_audio_id = audio_id.replace(".mp3", "")
   videoKey = f"{clean_audio_id}_{short_rand_string}.mp4"
   video_path = f'{APPLIO_AUDIO_OUTPUT_PATH}{videoKey}'

   # get the duration of the audio in seconds
   audio = AudioSegment.from_file(audio_file_path)
   audio_duration = len(audio) / 1000

   exit_code = os.system(f"ffmpeg -r 1 -loop 1 -y -t {audio_duration} -i {cover_image_path} -i {audio_file_path} -c:v h264_nvenc -shortest -pix_fmt yuv420p ${video_path}")

   if exit_code != 0:
      cleanup_files({"paths": [audio_file_path, cover_image_path, video_path]})
      logger.error("Failed to generate the video.")
      return {
         "status": "error",
         "error": "Failed to generate the video."
      }
   
   logger.info(f'Video generated successfully and saved in: {video_path}')
   
   file_upload_rs = upload_file(video_path, videoKey, BucketType.CONTENT_FILES)
   
   if file_upload_rs is None:
      raise Exception("Failed to upload the video file.")
   
   logger.info(f"Video uploaded successfully to R2. URL: {file_upload_rs}")
   
   # cleanup the files
   cleanup_files({"paths": [audio_file_path, cover_image_path, video_path]})

   return {
      "status": "success",
      "r2_video_url": file_upload_rs,
      "videoKey": videoKey,
      "audio_id": audio_id
   }
      
   
FastAPIInstrumentor.instrument_app(app=app, meter_provider=meter_provider, tracer_provider=tracer)