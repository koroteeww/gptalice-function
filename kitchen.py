import openai
import elevenlabs
from elevenlabs import set_api_key
from elevenlabs import generate  
from elevenlabs import save  
import os
import datetime
import random
import requests
import json
from moviepy.editor import *

#folder where new videos are stored
folder_vidnew = "/videosnew"
#folder for audio from video
folder_mp3 = "/mp3"
#folder for tts files
folder_tts = "/tts"
#elevenlabs files
folder_elevenlabs = "/eleven"
#ready files with sound over video (ffmpeg?)
folder_ready = "/ready"



processed_files=[]
new_files = []
mp3files=[]

def step1():
    # Open existing.txt file and form an array of processed files
    with open('processed.txt', 'r') as f:
        processed_files = f.read().splitlines()

    # Check certain folder for mp4 files
    mp4_files = []
    folder_path = folder_vidnew
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.mp4'):
            mp4_files.append(file_name)

    # Write new files to processed txt file
    with open('processed.txt', 'a') as f:
        for file_name in mp4_files:
            if file_name not in processed_files:
                f.write(file_name + '\n')
                fullpath = os.path.join(folder_path,file_name)
                new_files.append(fullpath)
    print("step1 complete.new mp4 files count="+str(new_files.count))

def step2():
    print("going to save as mp3 "+str(new_files.count))
    for mp4file in new_files:
        videoclip = VideoFileClip(mp4file)
        audioclip = videoclip.audio
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        rand_int = random.randint(0, 9999)        
        filename = f"audio_{now}_{rand_int}.mp3"
        fullpath = os.path.join(folder_mp3,filename)
        audioclip.write_audiofile(fullpath)
        videoclip.close()
        audioclip.close()
        mp3files.append(fullpath)

def step3():
    print("going to TTS "+str(mp3files.count))
    # Replace with your API key and audio file path
    API_KEY = 'your_yandex_api_key'
    for path in mp3files:
        # Read the audio file as binary data
        with open(path, 'rb') as f:
            audio_data = f.read()

        # Set the API endpoint and parameters
        url = 'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize'
        params = {
            'lang': 'ru-RU',
            'format': 'mp3',
            'sampleRateHertz': 44100
        }

        # Send the request with API key in headers and audio data in body
        response = requests.post(url, headers={'Authorization': f'Api-Key {API_KEY}'}, params=params, data=audio_data)

        # Parse the response JSON and extract the transcribed text
        response_json = json.loads(response.text)
        text = response_json['result']

        # Print the transcribed text
        print(text)
        print("going to Translate "+text)
        transl = step4(text,path)
        #now elevenlabs
        step5(transl,path)
        print("OK")

def step4(text,path):
    # Replace with your OpenAI API key  
    
    openaiapi_key = "your_openai_api_key"
    openaiclient = openai.Client(api_key=openaiapi_key)
    text = 'transcribed_text_in_russian'

    # Set the translation prompt
    prompt = (f"Translate the following text from Russian to Arabic:\n"
            f"{text}\n"
            f"Translation:")

    # Send the request with prompt and API key
    response = openaiclient.completions.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=4096,
        n=1,
        stop=None,
        temperature=0.1,
    )
    print(response)

    # Parse the response JSON and extract the translated text
    translated_text = response.choices[0].text.strip()

    # Print the translated text
    print(translated_text)
    txt=os.path.join(path,"_tts.txt")
    with open(txt,"w") as f:
        f.write(translated_text)
        print("saved at "+txt)
    return translated_text

def step5(translated,path):
    print("eleven labs")    
    set_api_key("YOUR_ELEVEN_API_KEY")  
  
    audio = generate(translated,model="eleven_multilingual_v2")
    save(audio,"test.wav")

def main():
    print("ULTIMATE CONTENT KITCHEN BY IVAN TOPP")
    step1()
    if (new_files.count>0):
        step2()
        step3()
    print("FINISHED")

main()
