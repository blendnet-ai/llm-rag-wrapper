from .repositories import OpenAIAssistantRepository
from OpenAIService.openai_service import OpenAIService
from typing import Any
from openai.types.beta.assistant import Assistant

class OpenAIAssistantWrapper:
    def __init__(self, assistant_name: str):
        self.assistant = OpenAIServiceWrapper.get_or_create_assistant(assistant_name)
    
    def get_response_using_file(self, file_path: str, prompt: str) -> str:
        thread = OpenAIService().create_thread()
        #message_file = OpenAIService().upload_file(file_path)
        #message = OpenAIService().create_message(thread.id, prompt, message_file)
        message = OpenAIService().create_message(thread.id, prompt)
        run = OpenAIService().run_assistant(thread.id, self.assistant.id)
        messages = OpenAIService().list_messages(thread.id)
        return messages

class OpenAIServiceWrapper:
    def get_or_create_assistant(name: str) -> Assistant:
        assistant_db = OpenAIAssistantRepository.get_assistant(name)
        return assistant_db
