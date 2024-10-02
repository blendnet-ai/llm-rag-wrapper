from django.db import models
from .enums import Assistant

class OpenAIAssistant(models.Model):
    assistant_id = models.CharField(max_length=500,blank=False)
    name = models.CharField(max_length=50, choices=[(assistant.name, assistant.role_details['name']) for assistant in Assistant])
    instructions = models.TextField(blank=False) 
    open_ai_model = models.CharField(max_length=500,blank=False)
    tools = models.JSONField(default=list,blank=False)



class Tool(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tool_code = models.TextField()
    default_values_for_non_llm_params = models.JSONField(default=dict,blank=True)
    tool_json_spec = models.JSONField(default=dict,blank=True)
    name = models.CharField(max_length=100)
    context_params = models.JSONField(default=list, blank=True)
    def __str__(self):
        return self.name



class PromptTemplate(models.Model):
    name = models.CharField(max_length=100)
    llm_config_name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, blank=True, null=True)
    required_kwargs = models.JSONField(blank=True,default=list, help_text="Required key words to be passed in user prompt template. If not provided by calling code, error will be raised. AS OF NOW, ERROR IS RAISED IF ANY KEYWORD IS MISSED, SINCE OTHERWISE $TEMPLATE_VAR LIKE THING WILL REMAIN IN PROMPT. FOR REQUIRED_KEYWORD ARGUMENTS FUNCTIONALITY, WE NEED DEFAULT VALUES OF OPTIONAL ARGS. CHECK IF THIS IS NEEDED, OR REMOVE REQUIRED KWARGS FIELD FROM HERE.")
    initial_messages_templates = models.JSONField(blank=True,default=list,help_text="Initial msgs in the format [{'role': 'assistant|user', 'content': '...'}]")
    system_prompt_template = models.TextField()
    user_prompt_template = models.TextField(blank=True, default="")
    logged_context_vars = models.JSONField(blank=True,default=list, help_text="Context variables to be logged in the chat log along with each user message, for later analysis.")
    tools = models.ManyToManyField(Tool,blank=True)


class ChatHistory(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    chat_history = models.JSONField(default=list)


class KnowledgeRepository(models.Model):
    class SourceType(models.IntegerChoices):
        AZURE_BLOB = 1, "Azure Blob"
        AMAZON_S3 = 2, "Amazon S3"
        GOOGLE_DRIVE = 3, "Google Drive"
    
    class Type(models.IntegerChoices):
        COURSE = 1, "Course"
    type =  models.IntegerField(choices=Type.choices)      
    source_path = models.CharField(max_length=255) 
    source_type = models.IntegerField(choices=SourceType.choices) 
    index_path = models.CharField(max_length=255, blank=True) 
    sas_token = models.CharField(max_length=255, blank=True) 
    


class ContentReference(models.Model):    
    class ContentType(models.TextChoices):
        PDF = 1, "PDF"
        YOUTUBE_VIDEO = 2, "YouTube Video"    
    content_type = models.IntegerField(choices=ContentType.choices)    
    path = models.CharField(max_length=255)  
    knowledge_repository_id = models.ForeignKey('KnowledgeRepository', on_delete=models.CASCADE, to_field='id')
