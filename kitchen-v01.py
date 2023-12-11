import openai
from openai import OpenAI
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

prfix="/root/kitchen"
#folder where new videos are stored
folder_vidnew = prfix+"/videosnew"
#folder for audio from video
folder_mp3 = prfix+"/mp3"
#folder for tts files
folder_tts = prfix+"/tts"
#elevenlabs files
folder_elevenlabs = prfix+"/eleven"
#ready files with sound over video (ffmpeg?)
folder_ready = prfix+"/ready"

OPENAIKEY = ""
YOUR_ELEVEN_API_KEY=""
client = OpenAI(api_key=OPENAIKEY)

processed_files=[]
new_files = []
mp3files=[]

langfrom="Russian"
lang_to=["English"]

vid_height = 1920
vid_width = 1080

def step1_searchmp4():
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
    print("step1 complete.new mp4 files count="+str(len(new_files)) )

def step2_getmp3audio(mp4file)->str:
    print("going to save as mp3 "+str(mp4file))    
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
    print("mp3 saved "+fullpath)
    return fullpath

def step3_tts(mp3path)->str:
    #using whisper speech to text
    print("going to speech to text "+str(mp3path))
    text=""
    # Read the audio file as binary data
    with open(mp3path, 'rb') as f:        
        res = client.audio.transcriptions.create(model='whisper-1',file=f)
        # Print the transcribed text
        print('Whisper STT text='+res.text)
        text=res.text
           
    return text
    
    

def step4_translate(text,lang="Arabic",source="Russian")->str:
   

    # Set the translation prompt
    prompt = f"Translate the following text from {source} to {lang} : "+ f"{text}"
    mmessages = [
            { "role": "system", "content": f"you are excellent and experienced translator from {source} to {lang}" },
            { "role": "user", "content": str(prompt) }
        ]
    # Send the request with prompt and API key
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=mmessages,
        max_tokens=2000,
        n=1,
        stop=None,
        temperature=0.1, 
        stream=False
    )

    print("OPENAI response for step4_translate:")
    #print(response)

    # Parse the response JSON and extract the translated text
    translated_text = response.choices[0].message.content

    # Print the translated text
    print(translated_text)
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_int = random.randint(0, 9999)        
    filename = f"stt_{now}_{rand_int}.txt"
    txt=os.path.join(folder_tts,filename)
    with open(txt,"w") as f:
        f.write(translated_text)
        print("saved at "+txt)
    return translated_text

def step5_generatefromtranslate(translated,lang="arabic")->str:
    print("eleven labs step 5:")    
    set_api_key(YOUR_ELEVEN_API_KEY)  
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    audio = generate(translated,model="eleven_multilingual_v2")
    fp = os.path.join(folder_elevenlabs,lang+f"_{now}_.wav")
    save(audio,fp)
    print("audio saved at "+fp)
    return fp

def step6_audiotovideo(newaudio,mp4file,lang="arabic"):
    print("join audio to video "+newaudio)
    
    videoclip = VideoFileClip(mp4file, resize_algorithm="bilinear",target_resolution=(vid_width,vid_height))
    
    #audioclip = videoclip.audio
    audioclip = AudioFileClip(newaudio)
    new_audioclip = CompositeAudioClip([audioclip])
    videoclip.audio = new_audioclip
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_int = random.randint(0, 9999)        
    filename = os.path.join(folder_ready,f"vid_{lang}_{now}_{rand_int}.mp4")
    videoclip.write_videofile(filename, codec="mpeg4")
    print("vid ok "+filename)
    videoclip.close()
    audioclip.close()
    return filename

def main():
    print("ULTIMATE CONTENT KITCHEN BY IVAN TOPP KOROTEEV")
    step1_searchmp4()
    if ( len(new_files) >0):
        for mp4file in new_files:
            mp3_path = step2_getmp3audio(mp4file)
            translation_tts = step3_tts(mp3_path)
            for llang in lang_to:
                translated_text = step4_translate(translation_tts,lang=llang,source=langfrom)
                genaratedaudio = step5_generatefromtranslate(translated_text,lang=llang)
                newvideofile = step6_audiotovideo(genaratedaudio,mp4file,lang=llang)
                print(f"RESULT of lang {llang} ="+newvideofile)

    print("FINISHED")

main()
