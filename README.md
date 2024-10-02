# README for Django LLM Interaction Wrapper

## Overview

This Django application serves as a flexible, reusable wrapper designed to facilitate interactions with various large language models (LLMs) and store configurations for tools, prompts, knowledge bases, etc. It allows users to define and integrate Python-based tools into prompt templates, enabling supported LLMs to utilize these tools seamlessly.

## Features

- **Configurable LLM Interaction**: Define and switch between multiple LLM configurations, including those from Azure, Gemini, and other platforms.
- **Tool Integration**: Create and manage tools that can be integrated into LLM interactions.
- **Prompt Template Management**: Define and manage templates for user and system prompts, ensuring dynamic and context-aware interactions.
- **Knowledge Repository**: Link to external knowledge sources like Azure Blob, Amazon S3, and Google Drive to enrich LLM responses.
- **Chat History Tracking**: Maintain and access the history of chats to analyze interactions and improve system responses over time.
- **Content Referencing**: Manage references to content types like PDFs and YouTube videos for use in LLM responses.

## Models

1. **OpenAIAssistant**: Manages different LLM configurations and their associated tools. (This is additional tool to directly interact with OpenAIAssistants)
2. **Tool**: Represents a tool with its associated code and parameters that can be used by LLMs.
3. **PromptTemplate**: Manages templates for initializing conversations and structuring prompts for the LLM.
4. **ChatHistory**: Stores the history of interactions for analysis.
5. **KnowledgeRepository**: Links to external repositories for storing and retrieving additional data. (This is currently in Beta phase)
6. **ContentReference**: Manages references to external content utilized by the LLM. (This is currently in Beta phase)

## Setup

### Requirements

- Django 4.x
- Python 3.11+
- OpenAI
- Litellm
  
### Installation
We will soon be converting this into a reusable package. Meanwhile, you can just copy this and use it as a custom app in your own repo.

### LLM Configurations

Define YAML files for different LLM configurations under the directory specified in `settings.LLM_CONFIGS_PATH`. Example YAML configurations are provided for various LLMs such as Azure and Gemini.

### Example YAMLs

```yaml
name: 'gpt-4-32k-azure'
llm_config_class: 'AzureOpenAILLMConfig'
endpoint: 'your-model-endpoint'
deployment_name: 'gpt4-32k'
api_key: '<api-key>'
api_version: '2024-02-15-preview'
tools_enabled: true
```

```yaml
name: 'gemini-pro'
llm_config_class: 'GeminiConfig'
endpoint: 'https://generativelanguage.googleapis.com/v1/models/gemini-1.0-pro:generateContent'
model_name: 'gemini-pro'
api_key: 'gemini-api-key'
tools_enabled: true
```
## Example usage

```python
# Example Usage for General Chat Interaction using Django LLM Wrapper

from your_app.models import ChatHistoryRepository, GenericChatDataRepository
from your_app.llm_interaction_wrapper import LLMCommunicationWrapper
from your_app.enums import ValidPromptTemplates

def handle_chat_interaction(user_id):
    # Retrieve existing chat data for the user
    chat_data = GenericChatDataRepository.get_chat_data_by_user_id(user_id)

    if chat_data.chat_history_obj is None:
        # If there is no existing chat history, initialize a new LLM wrapper
        context = {'user_id': user_id}  # Example context, can include more relevant data
        llm_wrapper = LLMCommunicationWrapper(prompt_name=ValidPromptTemplates.GENERAL_CHAT,
                                              chat_history_id=None,
                                              initialize=True,
                                              initializing_context_vars=context)
        
        # Generate an initial message to start the conversation
        message_text = "Hello! How can I assist you today?"
        message = {'role': 'assistant', 'content': message_text}

        # Add the initial message to the chat history
        llm_wrapper.chat_history_repository.add_msgs_to_chat_history([message], commit_to_db=True)

        # Update the chat data with the new chat history ID
        GenericChatDataRepository.add_chat_history_id(
            chat_data=chat_data,
            chat_history_id=llm_wrapper.get_chat_history_object().id
        )
    else:
        # If there is an existing chat history, continue using it
        llm_wrapper = LLMCommunicationWrapper(prompt_name=ValidPromptTemplates.GENERAL_CHAT,
                                              chat_history_id=chat_data.chat_history_obj.id)

    # Continue with the interaction logic here
    # e.g., processing user input, generating LLM responses, etc.
```


## Development

- Add new LLM configurations by extending the `LLMConfig` class.
- Develop new tools by defining Python code and integrating them into the `Tool` model.
- Create prompt templates as needed for different interaction scenarios.

## Coming Up

1. Basic Playground for Testing Prompt Templates
2. Support for RAG Implementation Using LlamaIndex

## Contributing

Contributions to enhance functionality, improve tools, or extend support for additional LLMs are welcome. Please submit pull requests or raise issues as needed.

## License
MIT License.
