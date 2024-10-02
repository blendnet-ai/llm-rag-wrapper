from openai import AzureOpenAI
import time
from speechai.settings import AZURE_OPENAI_API_KEY,AZURE_OPENAI_API_VERSION,AZURE_OPENAI_AZURE_ENDPOINT
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types import FileObject
from openai.types.beta.threads.run import Run
import logging
import litellm

class OpenAIService:
    def __init__(self):
        self.client = AzureOpenAI(api_key=AZURE_OPENAI_API_KEY,api_version=AZURE_OPENAI_API_VERSION,azure_endpoint=AZURE_OPENAI_AZURE_ENDPOINT)
        self.assistant_id: str = None
        self.logger = logging.getLogger(__name__)

    def get_assistant(self, id: str) -> Assistant:
        """
        Retrieve an assistant by its ID.
        """
        try:
            assistant = self.client.beta.assistants.retrieve(id)
            self.assistant_id = id
            return assistant
        except Exception as e:
            self.logger.error(f"An error occurred while retrieving the assistant: {e}")
            return None

    def create_assistant(self, name: str, instructions: str, tools: list, model: str) -> Assistant:
        """
        Create a new assistant with the given parameters.
        """
        try:
            assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                tools=tools,
                model=model,
            )
            self.assistant_id = assistant.id
            return assistant
        except Exception as e:
            self.logger.error(f"An error occurred while creating the assistant: {e}")
            return None

    def create_thread(self) -> Thread:
        """
        Create a new thread.
        """
        try:
            thread = self.client.beta.threads.create()
            self.logger.info("Thread created successfully.")
            return thread
        except Exception as e:
            self.logger.error(f"An error occurred while creating the thread: {e}")
            return None

    # def upload_file(self, file_path: str) -> FileObject:
    #     """
    #     Upload a file for use with the assistant.
    #     """
    #     try:
    #         with open(file_path, "rb") as file:
    #             message_file = self.client.files.create(
    #                 file=file, purpose="assistants"
    #             )
    #         self.logger.info("File uploaded successfully.")
    #         return message_file
    #     except Exception as e:
    #         self.logger.error(f"An error occurred while uploading the file: {e}")
    #         return None

    #def create_message(self, thread_id: str, prompt: str, message_file: FileObject):
    def create_message(self, thread_id: str, prompt: str):
        """
        Create a message in the given thread with the specified prompt and file attachment.
        """
        try:
            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role='user',
                content=prompt
                #attachments=[{"file_id": message_file.id, "tools": [{"type": "file_search"}]}]
            )
            self.logger.info("Message created successfully.")
            return message
        except Exception as e:
            self.logger.error(f"An error occurred while creating the message: {e}")
            return None

    def run_assistant(self, thread_id: str, assistant_id: str) -> Run:
        """
        Run the assistant in the specified thread.
        """
        try:
            if assistant_id is None:
                raise ValueError("Assistant ID is not set.")

            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
            )
            self.logger.info("Run started successfully.")
            
            # Wait for run to complete or fail
            while run.status not in ["completed", "failed", "canceled"]:
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                self.logger.info("Waiting for run to complete...")
                time.sleep(1)
            
            if run.status == "completed":
                self.logger.info("Run completed successfully!")
            else:
                self.logger.error(f"Run {run.status.capitalize()}!")
                self.logger.error(f"Error Code: {run.last_error.code}, message: {run.last_error.message}")
            
            return run
        except Exception as e:
            self.logger.error(f"An error occurred while running the assistant: {e}")
            return None

    def list_messages(self, thread_id: str) -> str:
        """
        List all messages in the given thread.
        """
        try:
            messages_str = ""
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            for message in reversed(messages.data):
                if message.role=='assistant':
                    messages_str=messages_str+message.content[0].text.value
            return messages_str
        except Exception as e:
            self.logger.error(f"An error occurred while listing the messages: {e}")
            return None
        
    @staticmethod
    def send_messages_and_get_response(messages: list, llm_config_params: dict):
        response = litellm.completion(
           **llm_config_params,
            messages=messages,
        )
        return response["choices"][0]
