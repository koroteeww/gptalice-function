import os
import openai
import datetime
import asyncio
import traceback
import logging
#YDB base
import ydb
import ydb.iam

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
answers = {}

CUT_WORD = ['Алиса', 'алиса']

users_state = {}
mlogger = logging.getLogger()

#chat GPT query
def aquery(message, prev_messages=None):
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

def execute_query(session):
  # Create the transaction and execute query.
  return session.transaction().execute(
    'select 1 as cnt;',
    commit_tx=True,
    settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
  )

def describe_table(session, path, name):
    fp = os.path.join(path, name)
    result = session.describe_table(fp)
    mlogger.warning("describe table: "+fp)
    for column in result.columns:
        mlogger.warning("column, name:"+ str(column.name) + ", type "+ str(column.type.item).strip())

def upsert_simple(session, path):
    
    session.transaction().execute(
        """
        PRAGMA TablePathPrefix("{}");
        UPSERT INTO gpt (id, session, request, response) VALUES
            ( 100500, 'test1','test2','test3' );
        """.format(path),
        commit_tx=True,
    )    
async def ask(request, messages ,uid):
    mlogger.warning('START_GPT response for GPT='+str(request))
    try:
        #reply = await aquery(request, messages)
        #messages = []
        all_messages = []
        all_messages.append(request)
        for m in all_messages:
            messages.append({"role": "user", "content": m})

        #chat = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages = messages,n=1)
        #completion = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages=messages, n=1)
        
        reply = 'some test'
        #completion.choices[0].message.content
        mlogger.warning('GPT ans='+reply)
        reply = reply.strip()
        endpoint = os.getenv('YDB_ENDPOINT')
        database=os.getenv('YDB_DATABASE')
        cred=ydb.iam.MetadataUrlCredentials()
        result=''
        #save to ydb
        # Create driver in global space.
        driver_config = ydb.DriverConfig(
        endpoint, database, credentials=cred)
        with ydb.Driver(driver_config) as driver:
            try:
                driver.wait(timeout=5)
                session = driver.table_client.session().create()
                upsert_simple(session,database)
                #describe_table(session,database,'gpt')
            except TimeoutError:
                mlogger.error("Connect failed to YDB")
                mlogger.error("Last reported errors by discovery:")
                mlogger.error(driver.discovery_debug_details())
                

        mlogger.warning("YDB OK res="+str(result))

    except Exception as e:
        traceback.print_exc()
        mlogger.error('ГДЕ ОТВЕТ СУКА '+str(e))
        reply = 'Не удалось получить ответ'
        
    answers[request] = reply
    mlogger.warning('END_GPT get response from gpt:'+str(datetime.datetime.now()) )
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
        
     
    mlogger.setLevel(logging.WARNING)    
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
            mlogger.warning("will run GPT with req="+request)
            asyncio.create_task(ask(request, messages,session_id))            
            #ask(request,messages)
            messages.append(request)
            session_state['messages'] = messages
            
            #print('no response')
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