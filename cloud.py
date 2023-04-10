import yandexcloud

from yandex.cloud.resourcemanager.v1.cloud_service_pb2 import ListCloudsRequest
from yandex.cloud.resourcemanager.v1.cloud_service_pb2_grpc import CloudServiceStub

def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    text = ''
    #testing cloud sdk
    cloud_service = yandexcloud.SDK().client(CloudServiceStub)
    clouds = {}
    for c in cloud_service.List(ListCloudsRequest()).clouds:
        clouds[c.id] = c.name
        
    if 'request' in event and \
            'original_utterance' in event['request'] \
            and len(event['request']['original_utterance']) > 0:
        text = event['request']['original_utterance']
    else:
        text = 'Hello! I\'ll repeat anything you say to me.'
        
    text = 'you said: '+text+' your clouds: '+str(clouds) 
    tts = text
    
    return {
        'version': event['version'],
        'session': event['session'],
        'response': {
            # Respond with the original request or welcome the user if this is the beginning of the dialog and the request has not yet been made.
            'text': text,
            'tts' : tts,
            # Don't finish the session after this response.
            'end_session': 'false'
        },
    }