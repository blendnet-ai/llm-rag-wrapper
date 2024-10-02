from django.apps import AppConfig
from django.conf import settings

class OpenAIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'OpenAIService'

    def ready(self) -> None:
        from OpenAIService.repositories import ValidLLMConfigs,ValidPromptTemplates
        if not settings.DISABLE_PROMPT_VALIDATIONS:
            ValidPromptTemplates().check_prompts_in_db()
            ValidLLMConfigs.check_llm_configs_in_db()






