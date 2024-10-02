import re
import typing
from datetime import datetime
import random
from string import Template
import logging
import json

from OpenAIService.llm_classes.LLMConfig import GLOBAL_LOADED_LLM_CONFIGS, LLMConfig
from OpenAIService.models import OpenAIAssistant, PromptTemplate, ChatHistory,Tool, KnowledgeRepository, ContentReference
from OpenAIService.openai_service import OpenAIService
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAIAssistantRepository:
    @staticmethod
    def get_assistant(name):
        """Created a fixture, from where we will store details about the assistant in DB.
            In this function just checking if id of assistant exists or not. If it doesn't
            exists create new id and store it for that assistant
        """
        try:
            assistant_from_db = OpenAIAssistant.objects.get(name=name)

            if assistant_from_db.assistant_id == '':
                new_assistant = OpenAIService().create_assistant(
                    name=assistant_from_db.name,
                    instructions=assistant_from_db.instructions,
                    tools=assistant_from_db.tools,
                    model=assistant_from_db.open_ai_model
                )

                assistant_from_db.assistant_id = new_assistant.id
                assistant_from_db.save()

                return new_assistant
            else:
                new_assistant = OpenAIService().get_assistant(id=assistant_from_db.assistant_id)
                return new_assistant


        except OpenAIAssistant.DoesNotExist:
            logging.error(f"Assistant not found for name: {name}")
            return None


class ValidLLMConfigs:
    AzureOpenAILLMConfig = 'AzureOpenAILLMConfig'

    @classmethod
    def get_all_valid_llm_configs(cls) -> list:
        return GLOBAL_LOADED_LLM_CONFIGS.keys()

    @classmethod
    def get_all_llm_configs_from_db(cls) -> list:
        return PromptTemplate.objects.all().values_list('llm_config_name', flat=True)

    @classmethod
    def check_llm_configs_in_db(cls) -> bool:
        llm_configs_in_db = ValidLLMConfigs.get_all_llm_configs_from_db()
        loaded_configs = cls.get_all_valid_llm_configs()
        missing_config_names = [config_name for config_name in loaded_configs if config_name not in llm_configs_in_db]
        if missing_config_names:
            raise ValueError(
                f"The following configs are missing from the configuration, but defined in DB: {missing_config_names} "
                f"To fix this, create these <name>.yaml files in {settings.LLM_CONFIGS_PATH} and restart the application.")
        return True


class ValidPromptTemplates:
    DEMO_PROMPT = "demo_prompt"
    ANOTHER_PROMPT = "another_prompt"
    CODE_REVISION_PROMPT = "code_revision_prompt"
    TEST_PROMPT = "test_prompt"
    DSA_PRACTICE = "dsa_practice_prompt"
    DOUBT_SOLVING = "doubt_solving"

    @classmethod
    def get_all_valid_prompts(cls) -> list:
        return [cls.TEST_PROMPT, cls.DSA_PRACTICE, cls.DOUBT_SOLVING]

    @classmethod
    def get_all_prompts_from_db(cls) -> list:
        return PromptTemplate.objects.all().values_list('name', flat=True)

    @classmethod
    def check_prompts_in_db(cls) -> bool:
        db_prompts = ValidPromptTemplates.get_all_prompts_from_db()
        code_prompts = cls.get_all_valid_prompts()
        missing_prompts = [prompt for prompt in code_prompts if prompt not in db_prompts]
        if missing_prompts:
            raise ValueError(f"The following prompts are missing from the database: {missing_prompts}. "
                             f"To fix this, set DISABLE_PROMPT_VALIDATIONS to True, start application and create these "
                             f"prompt templates in DB.")
        return True


class ChatHistoryRepository:

    def __init__(self, chat_history_id: int | None) -> None:
        if chat_history_id is None:
            self.chat_history_obj = ChatHistory.objects.create()
        else:
            self.chat_history_obj = ChatHistory.objects.get(id=chat_history_id)

    @staticmethod
    def create_new_chat_history(*, initialize=True) -> ChatHistory:
        self_instance = ChatHistoryRepository(chat_history_id=None)
        if initialize:
            pass

    def is_chat_history_empty(self):
        return len(self.chat_history_obj.chat_history) == 0

    def commit_chat_to_db(self):        
        self.chat_history_obj.save()

    @staticmethod
    def _generate_12_digit_random_id():
        min_num = 10 ** 11
        max_num = (10 ** 12) - 1
        return random.randint(min_num, max_num)

    def add_msgs_to_chat_history(self, msg_list: typing.List, timestamp: float = None, commit_to_db: bool = False) -> None:
        if not timestamp:
            timestamp = round(datetime.now().timestamp(), 1)
        for msg in msg_list:
            msg["timestamp"] = timestamp
            msg["id"]= self._generate_12_digit_random_id(),
        self.chat_history_obj.chat_history.extend(msg_list)
        if commit_to_db:
            self.commit_chat_to_db()

    def _add_user_msg_to_chat_history(self, *, msg_content: str, msg_timestamp: float) -> None:
        self._add_msg_to_chat_history(msg_content=msg_content, msg_type="user",
                                      msg_timestamp=msg_timestamp)

    def get_msg_list_for_llm(self) -> list:
        msg_list = []
        for msg in self.chat_history_obj.chat_history:
            if msg["role"] in ["user", "assistant", "system"]:
                new_msg = {"content": msg["content"], "role": msg["role"]}
            elif msg["role"] == "tool":
                new_msg = {"content": msg["content"],
                           "role": "tool",
                           "tool_call_id": msg["tool_call_id"],
                           "name": msg["name"]
                           }
            else:
                raise ValueError(f"Unexpected msg role: {msg['role']}")

            if "tool_calls" in msg:
                new_msg["tool_calls"] = msg["tool_calls"]
            msg_list.append(new_msg)
        return msg_list

    def add_or_update_system_msg(self, new_system_msg):
        if len(self.chat_history_obj.chat_history) > 0:
            if self.chat_history_obj.chat_history[0]["role"] == "system":
                self.chat_history_obj.chat_history[0]["content"] = new_system_msg
            else:
                raise ValueError(f"Unexpected: First msg is not a system msg. Chat id: {self.chat_history_obj.id}")
        else:
            self.chat_history_obj.chat_history = [{"role": "system", "content": new_system_msg}]


class LLMCommunicationWrapper:
    @staticmethod
    def convert_to_function(source_code: str):
        match = re.search(r'def\s+(\w+)\s*\(', source_code)
        if match:
            function_name = match.group(1)
        else:
            raise ValueError("No valid function definition found in the provided source code.")
        # Execute the source code in the current local scope
        exec(source_code, locals())
        # Retrieve and return the function by the extracted name
        return locals()[function_name]

    @staticmethod
    def package_function_response(was_success, response_string, timestamp=None):
        # formatted_time = get_local_time() if timestamp is None else timestamp
        packaged_message = {
            "status": "OK" if was_success else "Failed",
            "message": response_string,
            # "time": formatted_time,
        }

        return json.dumps(packaged_message, ensure_ascii=False)

    @staticmethod
    def parse_json(string) -> dict:
        """Parse JSON string into JSON with both json and demjson"""
        result = None
        try:
            result = json.loads(string, strict=True)
            return result
        except Exception as e:
            print(f"Error parsing json with json package: {e}")
            raise e
        # try:
        #     result = demjson.decode(string)
        #     return result
        # except demjson.JSONDecodeError as e:
        #     print(f"Error parsing json with demjson package: {e}")
        #     raise e

    @staticmethod
    def get_tool_context_params(tool_function_name, context_vars,context_params):
        context_params_json = {}
        for key in context_params:
            formatted_key = f'{key.strip("__")}'
            if formatted_key in context_vars:
                context_params_json[key] = context_vars[formatted_key]
            else:
                logger.error(f"Key '{key}' from context_params of tool not found in context_vars")
        return context_params_json

    def get_chat_history_object(self):
        return self.chat_history_repository.chat_history_obj

    def __init__(self, *, prompt_name, chat_history_id=None,
                 initialize=True, initializing_context_vars=None):
        self.prompt_name = prompt_name
        valid_templates = ValidPromptTemplates().get_all_valid_prompts()
        if prompt_name not in valid_templates:
            raise ValueError(f"Invalid prompt name: {prompt_name}")
        self.prompt_template = PromptTemplate.objects.get(name=prompt_name)
        self.chat_history_repository = ChatHistoryRepository(chat_history_id=chat_history_id)

        self.tool_json_specs = [{"type": "function", "function": tool.tool_json_spec} for tool in
                                self.prompt_template.tools.all()]
        self.tool_callables = {tool.name: LLMCommunicationWrapper.convert_to_function(tool.tool_code) for tool in
                               self.prompt_template.tools.all()}
        self.context_params = {tool.name: tool.context_params for tool in self.prompt_template.tools.all()}

        llm_config_instance: LLMConfig = GLOBAL_LOADED_LLM_CONFIGS[self.prompt_template.llm_config_name]
        self.llm_config_params = llm_config_instance.get_config_dict()
        if llm_config_instance.are_tools_enabled() and len(self.tool_json_specs):
            self.llm_config_params["tools"] = self.tool_json_specs
        elif len(self.tool_json_specs):
            raise ValueError(f"Tools not enabled in LLM config but used in LLM Prompt - {self.prompt_name}. "
                             f"LLM config name - {llm_config_instance.name}")
        self.to_be_logged_context_vars = self.prompt_template.logged_context_vars
        if initialize:
            if chat_history_id is not None:
                logger.error("Cannot initialize chat history if chat history is already created. Not initializing")
            else:
                self.initialize_chat_history(initializing_context_vars=initializing_context_vars, commit_to_db=True)

    def initialize_chat_history(self, *, initializing_context_vars=None, commit_to_db=True):
        if initializing_context_vars is None:
            initializing_context_vars = {}
        system_prompt = Template(self.prompt_template.system_prompt_template).substitute(initializing_context_vars)
        init_msg_list = [{"role": "system", "content": system_prompt}]
        for msg in self.prompt_template.initial_messages_templates:
            init_msg_list.append({"content": Template(msg["content"]).substitute(initializing_context_vars),
                                  "role": msg["role"],
                                  "system_generated": True,
                                  "show_in_user_history": False,
                                  })
        self.chat_history_repository.add_msgs_to_chat_history(init_msg_list)
        if commit_to_db:
            self.chat_history_repository.commit_chat_to_db()

    def handle_tool_call(self, choice_from_llm,context_vars):
        if choice_from_llm["message"].get("tool_calls") is None:
            return {}
        tool_call_message = choice_from_llm["message"]
        tool_call_instancd = tool_call_message["tool_calls"][0]
        result = tool_call_instancd["function"]
        tool_call_id = tool_call_instancd["id"]
        tool_function_name = result.get("name", None)
        if tool_function_name not in self.tool_callables:
            logger.error(
                f"Unexpected tool call - {tool_function_name}. Chat id - {self.chat_history_repository.chat_history_obj.id}")
            return {}
        json_tool_function_params = result.get("arguments", {})
        tool_function_params = LLMCommunicationWrapper.parse_json(json_tool_function_params)
        context_params = self.context_params[tool_function_name]
        # Initialize context_params_json as an empty dictionary
        context_params_json = LLMCommunicationWrapper.get_tool_context_params(tool_function_name, context_vars,context_params)
        try:
            tool_output = self.tool_callables[tool_function_name](**context_params_json,**tool_function_params)
            logger.info(f"Got tool output of {tool_function_name} - {tool_output}")
            tool_output_packaged = LLMCommunicationWrapper.package_function_response(True, str(tool_output))
            logger.info(f"Generated packaged tool response = f{tool_output_packaged}")
        except Exception as exc:
            logger.error(f"Error in tool call - {exc}. Chat id - {self.chat_history_repository.chat_history_obj.id}")
            tool_output_packaged = LLMCommunicationWrapper.package_function_response(False, "Got error in tool call")

        tool_call_msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [tool_call_instancd.dict()],
            "tool_call_id": tool_call_id,
        }
        
        our_tool_response = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_function_name,
            "content": tool_output_packaged
        }
        existing_msg_list = self.chat_history_repository.get_msg_list_for_llm()
        new_msg_list = existing_msg_list + [tool_call_msg, our_tool_response]
        a_time = datetime.now().timestamp()
        post_tool_call_response = OpenAIService.send_messages_and_get_response(new_msg_list, self.llm_config_params)
        post_tool_call_response_dict = {
            "role": "assistant",
            "message_generation_time": round(datetime.now().timestamp() - a_time, 1),
            "content": post_tool_call_response["message"]["content"],
        }
        tool_call_msg['context_params']=context_params_json
        self.chat_history_repository.add_msgs_to_chat_history(
            [tool_call_msg, our_tool_response, post_tool_call_response_dict])
        self.chat_history_repository.commit_chat_to_db()
        tool_data = {
                        "used_tool": tool_function_name,
                        "tool_calls": [tool_call_instancd.dict()],
                        "tool_content": tool_output_packaged
                    }
        modified_message_content = {"type":"bot","message":post_tool_call_response["message"]["content"],"tool_data":tool_data}
        return modified_message_content


    def get_one_time_completion(self, kwargs):
        # Fetch the prompt template from the database by name
        prompt_template = PromptTemplate.objects.get(name=self.prompt_name)

        required_keys = prompt_template.required_kwargs

        # Check if all required keys are present in kwargs
        missing_keys = [key for key in required_keys if required_keys[key] and key not in kwargs]
        if missing_keys:
            error_message = f"Missing required keys: {', '.join(missing_keys)}"
            logging.error(error_message)
            raise ValueError(error_message)

        # Access system_prompt and user_prompt fields
        system_prompt = prompt_template.system_prompt_template
        user_prompt = prompt_template.system_prompt_template

        # Substitute values in the prompts using kwargs
        formatted_system_prompt = system_prompt
        formatted_user_prompt = user_prompt

        for key, value in kwargs.items():
            formatted_system_prompt = formatted_system_prompt.replace(f"${key}", str(value))
            formatted_user_prompt = formatted_user_prompt.replace(f"${key}", str(value))

        combined_prompt = {'system_prompt': formatted_system_prompt, 'user_prompt': formatted_user_prompt}

        return combined_prompt

    def get_final_user_message(self, user_msg: str, context_vars=None) -> dict:
        user_prompt = user_msg
        if self.prompt_template.user_prompt_template:
            user_prompt = Template(self.prompt_template.user_prompt_template).substitute(**context_vars, user_msg=user_msg)
        return {"role":"user", "content":user_prompt}

    def send_user_message_and_get_response(self, user_msg: str, context_vars=None) -> str:
        if context_vars is None:
            context_vars = {}
        required_keys = self.prompt_template.required_kwargs
        logged_context_vars = self.prompt_template.logged_context_vars
        missing_keys = [key for key in required_keys if key not in context_vars]
        logger.info(f"Required keys: {required_keys}. Missing keys: {missing_keys}.")
        if missing_keys:
            error_message = f"Missing required keys: {', '.join(missing_keys)}"
            raise ValueError(error_message)
        
        filtered_context_vars = {key: value for key, value in context_vars.items() if key in logged_context_vars}
        self.update_chat_history(context_vars)
        new_msg_list = self.chat_history_repository.get_msg_list_for_llm()
        new_msg_list += [self.get_final_user_message(user_msg, context_vars=context_vars)]

        # The user msg is added here, but in case of tool call we are committing to db only post handling of tool
        # call. ALSO, User msg in history and the one sent to llm finally are intentionally different
        self.chat_history_repository.add_msgs_to_chat_history(
            [{"role": "user", "content": user_msg, "context_vars": filtered_context_vars}])
        a_time = datetime.now().timestamp()
        choice_response = OpenAIService.send_messages_and_get_response(new_msg_list, self.llm_config_params)

        if choice_response["message"].get("tool_calls") is not None:
            return self.handle_tool_call(choice_response,context_vars)
        else:
            response_msg_content = choice_response["message"]["content"]
            self.chat_history_repository.add_msgs_to_chat_history(
                [{"role": "assistant",
                  "message_generation_time": round(datetime.now().timestamp() - a_time,1),
                  "content": response_msg_content}])
            self.chat_history_repository.commit_chat_to_db()
            return response_msg_content

    def update_chat_history(self, context_vars: None):
        if context_vars is None:
            context_vars = {}
        is_chat_history_empty = self.chat_history_repository.is_chat_history_empty()
        system_prompt = Template(self.prompt_template.system_prompt_template).substitute(**context_vars)

        if not is_chat_history_empty:
            self.chat_history_repository.add_or_update_system_msg(system_prompt)
        else:
            self.initialize_chat_history(initializing_context_vars=context_vars, commit_to_db=False)
            # init_msg_list = [{"role": "system", "content": system_prompt}]
            # for msg in self.prompt_template.initial_messages_templates:
            #     init_msg_list.append({"content": Template(msg["content"]).substitute(**context_vars),
            #                           "role": msg["role"],
            #                           "system_generated":True,
            #                           "show_in_user_history": False,
            #                           })
            # self.chat_history_repository.add_msgs_to_chat_history(init_msg_list)
    

    @staticmethod
    def get_processed_chat_messages(chat_history,is_superuser):
        messages_list = []  # Initialize list to store processed messages
        mapping = {"user": "user", "assistant": "bot"}
        for i, msg in enumerate(chat_history):
            if msg.get("show_in_user_history", True) == False:
                    continue
            # Check if the message role is valid and it is not a tool call or initial message
            if msg["role"] in mapping and not msg.get("tool_calls") and not msg.get("initial_message", None):
                msg_type = mapping[msg["role"]]  # Map the role to its type
                message_content = msg["content"]
                extra = {}  # Initialize extra information dictionary

                # If the user is a superuser, include tool information
                if is_superuser and i > 0 and chat_history[i-1]["role"] == "tool":
                    used_tool = chat_history[i-1]["name"]
                    tool_calls = chat_history[i-2].get("tool_calls", [])
                    content = chat_history[i-1]["content"]
                    extra = {
                        "used_tool": used_tool,
                        "tool_calls": tool_calls,
                        "tool_content": content
                    }

                # Append the message and additional information to the list
                messages_list.append({
                    "message": message_content,
                    "type": msg_type,
                    "tool_data": extra
                })

        return messages_list


class KnowledgeRepositoryRepository:
    @staticmethod
    def create_knowledge_repository(type, organization, api_key, course_id, source_path, source_type, index_path, sas_token):
        knowledge_repository =KnowledgeRepository(
            type=type,
            organization=organization,
            api_key=api_key,
            course_id=course_id,
            source_path=source_path,
            source_type=source_type,
            index_path=index_path,
            sas_token=sas_token
        )
        knowledge_repository.save()
        return knowledge_repository


class ContentReferenceRepository:
    @staticmethod
    def create_content_reference(content_type, course_id, path, knowledge_repository_id):
        content_reference = ContentReference(
            content_type=content_type,
            course_id=course_id,
            path=path,
            knowledge_repository_id=knowledge_repository_id
        )

        content_reference.save()
        return content_reference

    @staticmethod
    def get(id):
        return ContentReference.objects.get(id=id)
