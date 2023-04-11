import os

import openai

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

    
async def aquery(message, prev_messages=None):
    messages = []
    if not prev_messages:
        all_messages = []
    else:
        all_messages = prev_messages.copy()
    all_messages.append(message)
    for m in all_messages:
        messages.append({"role": "user", "content": m})
    #system
    messages.append({"role": "system", "content": 'you are a helpful tutor for learn english, your role is to answer to user, and provide feedback about grammar and words usage'})

    chat = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages = messages,n=1)
    reply = chat.choices[0].message.content
    reply = reply.strip()
    return reply
