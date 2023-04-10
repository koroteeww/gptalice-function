import os
import openai
import datetime
import asyncio
import traceback



OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
answers = {}

CUT_WORD = ['Алиса', 'алиса']

users_state = {}

#chat GPT query
async def aquery(message, prev_messages=None):
    print('CODE at aquery')
    messages = []
    if not prev_messages:
        all_messages = []
    else:
        all_messages = prev_messages.copy()
    all_messages.append(message)
    for m in all_messages:
        messages.append({"role": "user", "content": m})

    #chat = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages = messages,n=1)
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, n=1)
    print(completion.choices[0].message.content)
    reply = completion.choices[0].message.content
    reply = reply.strip()
    return reply
    
async def ask(request, messages):
    print('START_GPT response for GPT='+str(request))
    try:
        reply = await aquery(request, messages)
    except Exception as e:
        traceback.print_exc()
        print('ГДЕ ОТВЕТ СУКА '+e)
        reply = 'Не удалось получить ответ'
        
    answers[request] = reply
    print('END_GPT get response from gpt:', datetime.datetime.now(tz=None))
    return reply
    
async def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    text = ''
    session_id = event['session'].get('session_id')
    if session_id and not session_id in users_state:
        users_state[session_id] = {
            'messages': [],
        }
        
    if session_id:
        session_state = users_state[session_id]
    else:
        session_state = {}
        
        
    #req=event
    #res=context
    tts=''
    reply=''
    #acyns
    #loop = asyncio.get_event_loop()
    #asyncio.set_event_loop(loop)
    #MAIN:
    if 'request' in event and \
            'original_utterance' in event['request'] \
            and len(event['request']['original_utterance']) > 0:  
                  
        messages = session_state.get('messages', [])
        request = event['request']['original_utterance']
        for word in CUT_WORD:
            if request.startswith(word):
                request = request[len(word):]
        request = request.strip()


        if 'message' not in session_state:
            task = asyncio.create_task(ask(request, messages))            
            messages.append(request)
            session_state['messages'] = messages
            if task.done():
                reply = task.result()
                del answers[request]
            else:
                print('no response')
                reply = 'Не успел получить ответ. Спросите позже'
                tts = reply + '<speaker audio="alice-sounds-things-door-2.opus">'
                session_state['message'] = request
        else:
            old_request = session_state['message']
            if old_request not in answers:
                reply = 'Ответ пока не готов, спросите позже'
                tts = reply + '<speaker audio="alice-sounds-things-door-2.opus">'
            else:
                answer = answers[old_request]
                del answers[old_request]
                del session_state['message']
                reply = f'Отвечаю на предыдущий вопрос "{old_request}"\n {answer}'
                tts = reply
    else:
        reply = 'Я умный чат бот. Спроси что-нибудь'
        tts=reply
        ## Если это первое сообщение — представляемся
    
    
        
    return {
        'version': event['version'],
        'session': event['session'],
        'response': {
            # Respond with the original request or welcome the user if this is the beginning of the dialog and the request has not yet been made.
            'text': reply,
            'tts' : tts,
            # Don't finish the session after this response.
            'end_session': 'false'
        },
    }