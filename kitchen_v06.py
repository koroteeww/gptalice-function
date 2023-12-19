import openai
from openai import OpenAI
import elevenlabs
from elevenlabs import set_api_key
from elevenlabs import generate  
from elevenlabs import save  
from elevenlabs import voices
from elevenlabs import Voice
from elevenlabs import Voices

import os
import datetime
import random
import requests
import json
from moviepy.editor import *
import subprocess

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

#cloning
CLONING=False
Voicename="Cloned_Voice2023-12-13_14-18-18"
#lang from and list of lang to
langfrom="Russian"
whisperlang = "ru" #en
lang_to=["English","Spanish"]
#lang_to=["Chinese","English","Spanish","Hindi","Arabic","French"]

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
    rand_int = random.randint(0, 999)  
    ff = str(os.path.basename(mp4file))
    ff = ff.replace('.','_')    
    filename = f"audio_from_{ff}_{now}_{rand_int}.mp3"
    fullpath = os.path.join(folder_mp3,filename)
    audioclip.write_audiofile(fullpath)
    videoclip.close()
    audioclip.close()
    mp3files.append(fullpath)
    print("mp3 saved "+fullpath)
    return fullpath

def step2_getmp3list(orig_mp3):
    silencetuples=[]
    #produce a dict where key is file path and value is tuple - From and To seconds
    pathesmp3={}
    #dict with path as key and start second as value
    cmd=f"ffmpeg -i {orig_mp3} -af silencedetect=n=-40dB:d=0.35 -f null - 2> /root/kitchen/flog.txt"
    subprocess.call(cmd,shell=True)   
    #now read the log
    import re
    index=0
    prev=0
    silences=[]
    
    with open("/root/kitchen/flog.txt","r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]        
        for lline in lines:
            if "silence_start" in lline:
                silence_st_match = re.search(r'silence_start: ([\d.]+)', lline)
                silence_start = float(silence_st_match.group(1))   
            if "silence_end" in lline:
                silence_end_match = re.search(r'silence_end: ([\d.]+)', lline)
                silence_end = float(silence_end_match.group(1))   
                      
                silencetuples.append((silence_start,silence_end))
                if (index==0): 
                    value_at_index=(0.1,silence_end)
                    prev=silence_end
                else:                     
                    value_at_index=(prev,silence_end)
                    prev=silence_end
                silences.append(value_at_index)
                index=index+1

    #ffmpeg -i input.mp3 -to 1.20837 -c copy output_01.mp3
    #ffmpeg -i input.mp3 -ss 1.92546 -to 3.51778 -c copy output_02.mp3            
    print("silences:")
    print(silencetuples)
    print("silences 22 in mp3:")
    print(silences)

    index=1
    for tuples in silences: 
        st = tuples[0]
        end = tuples[1]
        ff = str(os.path.basename(orig_mp3))
        ff = ff.replace('.','_')    
        filename = f"chunk_{index}_{ff}.mp3"
        fullpath = os.path.join(folder_mp3,filename)
        out=fullpath
        cmdd=f"ffmpeg -y -i {orig_mp3} -ss {st} -to {end} -c copy {out} -loglevel quiet"
        subprocess.call(cmdd,shell=True)  
        index=index+1
        pathesmp3[fullpath]=tuples

    return pathesmp3,silencetuples

def step3_stt(mp3path)->str:
    #using whisper speech to text
    print("going to speech to text "+str(mp3path))
    text=""
    # Read the audio file as binary data
    with open(mp3path, 'rb') as f:        
        res = client.audio.transcriptions.create(model='whisper-1',file=f, language=whisperlang)
        # Print the transcribed text
        print('Whisper STT text='+res.text)
        text=res.text
    #save whisper log
    with open("whisperLog.txt","a", encoding="utf-8") as log:
        log.write(f"Whisper response to {mp3path} is: {text} \r\n")
                   
    return text
    
    

def step4_translate(text,lang="Arabic",source="Russian")->str: 
    # Set the translation prompt
    prompt = f"Translate the following text from {source} to {lang}! "
    prompt = prompt + "And if you can not translate or have errors, just retutrn empty string as answer!" 
    prompt = prompt + " Very important, the incoming text is from recognized speech, so try your best to fit the same pronounciation lenth! "
    prompt = prompt + "Text: "+ f"{text}"

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
    filename = f"stt_translate_{now}_{rand_int}.txt"
    txt=os.path.join(folder_tts,filename)
    with open(txt,"w") as f:
        f.write(translated_text)
        print("saved at "+txt)
    return translated_text

def step5_generatefromtranslate(translated,lang="arabic",vvoice=None)->str:
    print("eleven labs generate:")    
    set_api_key(YOUR_ELEVEN_API_KEY)  
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if CLONING:
        #cloned from mp3
        audio = generate(translated,model="eleven_multilingual_v2",voice=vvoice)
    elif vvoice is not None:
        #some predefined cloned voice
        audio = generate(translated,model="eleven_multilingual_v2", voice=vvoice)    
    else:
        #some default voice
        audio = generate(translated,model="eleven_multilingual_v2")

    fp = os.path.join(folder_elevenlabs,lang+f"_{now}.wav")
    save(audio,fp)
    print("audio saved at "+fp)
    return fp

def step6_audiotovideo(newaudio,mp4file,lang="arabic"):
    if (os.path.exists(newaudio)==False):
        return "newaudio NO EXIST!!!"
    
    print("join audio to video "+str(newaudio))    
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_int = random.randint(0, 999)        
    ff = str(os.path.basename(mp4file))
    ff = ff.replace('.','_')
    filename = os.path.join(folder_ready,f"vid_from_{ff}_{lang}_{now}_{rand_int}.mp4")
    join_audio_video(newaudio,mp4file,filename)
    return filename

def join_audio_video(audio_file, video_file, output_file):
    cmd = f"ffmpeg -i {video_file} -i {audio_file}  -c:v libx264 -crf 23 -c:a aac -map 0:v:0 -map 1:a:0 {output_file} -loglevel quiet"
    print("cmd="+str(cmd))
    subprocess.call(cmd,shell=True)
    print("ffmpeg finished")

def vclone(mp3):
    print("CLONING...")
    from elevenlabs import clone
    set_api_key(YOUR_ELEVEN_API_KEY)  
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    voice = clone(name = "Cloned_Voice"+now, files = [mp3])      
    print("CLONING OK!")
    return voice

def getvoices():
    set_api_key(YOUR_ELEVEN_API_KEY)  
   
    lv = voices()
    vv=None
    print("Elevenlabs cloned voices:")
    for v in lv:
        if v.category=='cloned':                        
            if (v.name==Voicename):
                vv=v
                print(v.voice_id+" "+v.name)

    return vv

def get_wav_duration(filepath)->float:
    clip = AudioFileClip(filepath) 
    return clip.duration

def ffconcat(gen_audios,pauses,lang="arabic"):
    #use mp3list - a dict where we have silences tuples
    #so we don't just concat but use silences
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fp = os.path.join(folder_elevenlabs,"res_"+lang+f"_{now}.wav")
    fp = concatenate_wav_files_with_pauses(gen_audios, pauses, fp,lang)    
    return fp

# Function to concatenate WAV files with pauses
def concatenate_wav_files_with_pauses(wav_files, pauses, output_filepath,lang):
    input_file_list = []
    sumd=0
    maxp=0        
    print("SILENCE PRODUCED...")
    # Create a text file containing the list of WAV files and pauses
    for i, wav_file in enumerate(wav_files):
        input_file_list.append("file '{}'".format(wav_file))
        fname="silence{}.wav".format(i)
        thesilencepath = os.path.join(folder_elevenlabs,fname)
        duration = get_wav_duration(wav_file)        
        sumd = sumd + duration
        # Add silence file for each pause, except for the last pause
        if i < len(pauses):
            pause_curr = pauses[i]
            pause_end = pause_curr[1]
            if (i==0): 
                pause_start = duration
            else: 
                pause_start = pauses[i-1][1] + duration
            #add a bit 0.3 second    
            pause_duration = pause_end - pause_start + 0.30

            if (pause_duration<0): pause_duration = -1 * pause_duration

            print(f"SILENCE from {pause_start} sec, duration {pause_duration} sec")
            if (pause_end > maxp): maxp=pause_end
            sumd= sumd + pause_duration
            subprocess.call("ffmpeg -loglevel quiet -y -f lavfi -c:a pcm_s16le -i anullsrc -t {} {}".format(pause_duration, thesilencepath), shell=True)
            #normalize
            norms = normalizewav(thesilencepath)
            input_file_list.append("file '{}'".format(norms))

    fname=f'input_{lang}.txt'
    # Create a text file containing the list of WAV files and pauses
    with open(fname, 'w') as input_file:
        input_file.write('\n'.join(input_file_list))
    
    print("total duration: "+str(sumd)+" maxp="+str(maxp))
    if (sumd>maxp): maxp=sumd
    #amerge v2
    concat_command2 = "ffmpeg -loglevel quiet -safe 0 -t {} -f concat  -i {} -filter_complex amerge -c:a pcm_s16le -y {}".format(maxp,fname,output_filepath)
    # Concatenate the audio files while adding the silent pauses
    concat_command = "ffmpeg -loglevel quiet -safe 0 -y -t {} -f concat -i {} -c:a pcm_s16le {} ".format(maxp,fname,output_filepath)

    subprocess.call(concat_command, shell=True)
    thenorm = normalizewav(output_filepath)
    return thenorm

def normalizewav(incwav)->str:
    fb=os.path.basename(incwav)
    output = os.path.join(folder_elevenlabs,fb+"_N.wav")
    #normalize
    cmdn=f"ffmpeg -loglevel quiet -y -i {incwav} -af loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-27:measured_TP=-5:measured_LRA=7:linear=true -c:a pcm_s16le {output}"    
    subprocess.call(cmdn, shell=True)
    return output

def isNotBlank (myString):
    return bool(myString and myString.strip())
def isBlank (myString):
    return not (myString and myString.strip())

def is_null_or_whitespace(text)->bool:
    return text is None or len(text.strip()) == 0 

def checkstt_ok(stttext, lang)->bool:
    # If a match is found, the function returns `True`, 
    #indicating that Russian symbols, spaces, or punctuation signs are present in the string.
    import re
    import string
    pattern = r'[\s'+ re.escape(string.punctuation) + ']'
    if (lang=="Russian"): 
        pattern = r'[а-яА-Я]'
    elif (lang=="English"):
        pattern = r'[a-zA-Z]'   
    matches = re.match(pattern,stttext) 
    if matches is None: return False
    grups = matches.group()   
    return len(grups)>0


   
def main():
    print("ULTIMATE CONTENT KITCHEN BY IVAN TOPP KOROTEEV")
    step1_searchmp4()
    voice=None
    
    
    if ( len(new_files) >0):
        for mp4file in new_files:
            print("working with "+mp4file)
            mp3_path = step2_getmp3audio(mp4file)
            mp3list, pauses = step2_getmp3list(mp3_path)
            print("mp3 files get "+str(len(mp3list)))
            #print(mp3list)
            
            textstt=[]
            for chunk in mp3list:
                translation_stt = step3_stt(chunk)
                if (checkstt_ok(translation_stt, langfrom) and is_null_or_whitespace(translation_stt)==False):
                    textstt.append(translation_stt)
                else:
                    print("STT FAIL at "+chunk)    
            lench=len(mp3list)   
            lenstt=len(textstt)     
            print(f"Speech to text done. Chunks {lench} stt {lenstt}")
            
            #optional cloning
            if CLONING:
                voice = vclone(mp3_path)
            else:
                if (voice is None): 
                    voice = getvoices()

            for llangto in lang_to:
                gen_audios=[]
                for text in textstt: 
                    translated_text = step4_translate(text,lang=llangto,source=langfrom)
                    if (isBlank(translated_text)): continue              
                    genaratedaudio = step5_generatefromtranslate(translated_text,lang=llangto,vvoice=voice)
                    #normalize wav
                    normalizedaudio = normalizewav(genaratedaudio)
                    gen_audios.append(normalizedaudio)
                #join audios
                print("-Concat generated audios "+str(len(gen_audios)))
                totalaudio=ffconcat(gen_audios,pauses,llangto)
                newvideofile = step6_audiotovideo(totalaudio,mp4file,lang=llangto)
                print(f"RESULT of lang {llangto} ="+newvideofile)
            print("cycle complete")

    print("FINISHED")

main()

#getvoices()

#еще один вариант - это взять SSML с паузами <break time="2350ms"/>.
#то есть я знаю оригинальные куски аудио (чанки) и я знаю сколько длится сгенерированный Elevenlabs результат
#то есть идея в том что мы в цикле по оригинальным чанкам идем и смотрим длительность результата и добавляем в запрос к Elevenlabs паузу break
#и заново генерируем длительность



