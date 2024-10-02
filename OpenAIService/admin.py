# admin.py
import inspect
import json
import logging
import re
import typing
from typing import Optional, get_args, get_origin

from django.contrib import admin
from django.db import models
from django import forms
from django.core.exceptions import ValidationError
from docstring_parser import parse
from codemirror2.widgets import CodeMirrorEditor
from django_json_widget.widgets import JSONEditorWidget
from .llm_classes.LLMConfig import GLOBAL_LOADED_LLM_CONFIGS
from .models import OpenAIAssistant, ChatHistory, PromptTemplate, Tool, KnowledgeRepository, ContentReference
from .serializers import OpenAIAssistantSerializer

logger = logging.getLogger(__name__)

def is_optional(annotation):
    # Check if the annotation is a Union
    if getattr(annotation, "__origin__", None) is typing.Union:
        # Check if None is one of the options in the Union
        return type(None) in annotation.__args__
    return False

def optional_length(annotation):
    if is_optional(annotation):
        # Subtract 1 to account for NoneType
        return len(annotation.__args__) - 1
    else:
        raise ValueError("The annotation is not an Optional type")

def type_to_json_schema_type(py_type):
    """
    Maps a Python type to a JSON schema type.
    Specifically handles typing.Optional and common Python types.
    """
    # if get_origin(py_type) is typing.Optional:
    if is_optional(py_type):
        # Assert that Optional has only one type argument
        type_args = get_args(py_type)
        assert optional_length(py_type) == 1, f"Optional type must have exactly one type argument, but got {py_type}"

        # Extract and map the inner type
        return type_to_json_schema_type(type_args[0])

    # Mapping of Python types to JSON schema types
    type_map = {
        int: "integer",
        str: "string",
        bool: "boolean",
        float: "number",
        list[str]: "array",
        # Add more mappings as needed
    }
    if py_type not in type_map:
        raise ValueError(f"Python type {py_type} has no corresponding JSON schema type")

    return type_map.get(py_type, "string")  # Default to "string" if type not in map

def generate_schema(function, name: Optional[str] = None, description: Optional[str] = None):
    # Get the signature of the function
    sig = inspect.signature(function)

    # Parse the docstring
    docstring = parse(function.__doc__)

    # Prepare the schema dictionary
    schema = {
        "name": function.__name__ if name is None else name,
        "description": docstring.short_description if description is None else description,
        "parameters": {"type": "object", "properties": {}, "required": []},
    }

    for param in sig.parameters.values():
        # Exclude 'self' parameter
        if param.name == "self":
            continue

        # Assert that the parameter has a type annotation
        if param.annotation == inspect.Parameter.empty:
            raise TypeError(f"Parameter '{param.name}' in function '{function.__name__}' lacks a type annotation")

        # Find the parameter's description in the docstring
        param_doc = next((d for d in docstring.params if d.arg_name == param.name), None)

        # Assert that the parameter has a description
        if not param_doc or not param_doc.description:
            raise ValueError(
                f"Parameter '{param.name}' in function '{function.__name__}' lacks a description in the docstring")

        # if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
        #     schema["parameters"]["properties"][param.name] = pydantic_model_to_open_ai(param.annotation)
        # else:
        #
        # Add parameter details to the schema
        param_doc = next((d for d in docstring.params if d.arg_name == param.name), None)
        schema["parameters"]["properties"][param.name] = {
            # "type": "string" if param.annotation == str else str(param.annotation),
            "type": type_to_json_schema_type(
                param.annotation) if param.annotation != inspect.Parameter.empty else "string",
            "description": param_doc.description,
        }
        if param.default == inspect.Parameter.empty:
            schema["parameters"]["required"].append(param.name)

        if get_origin(param.annotation) is list:
            if get_args(param.annotation)[0] is str:
                schema["parameters"]["properties"][param.name]["items"] = {"type": "string"}

        if param.annotation == inspect.Parameter.empty:
            schema["parameters"]["required"].append(param.name)

    # append the heartbeat
    # if function.__name__ not in NO_HEARTBEAT_FUNCTIONS:
    #     schema["parameters"]["properties"][FUNCTION_PARAM_NAME_REQ_HEARTBEAT] = {
    #         "type": FUNCTION_PARAM_TYPE_REQ_HEARTBEAT,
    #         "description": FUNCTION_PARAM_DESCRIPTION_REQ_HEARTBEAT,
    #     }
    #     schema["parameters"]["required"].append(FUNCTION_PARAM_NAME_REQ_HEARTBEAT)

    return schema


class OpenAIAssistantAdmin(admin.ModelAdmin):
    list_display = ('assistant_id', 'name', 'open_ai_model', 'tools')
    search_fields = ('assistant_id', 'name', 'open_ai_model', 'tools')

    def save_model(self, request, obj, form, change):
        # Use the serializer to validate and save the data
        serializer = OpenAIAssistantSerializer(instance=obj, data=form.cleaned_data)
        if serializer.is_valid():
            serializer.save()
        else:
            # Handle serializer errors if needed
            raise ValueError("Serializer data is invalid")



class ToolAdminForm(forms.ModelForm):
    class Meta:
        model = Tool
        widgets = {
            'tool_code': CodeMirrorEditor(options={'mode': 'javascript','cols':80},themes=["neat"]),
        }
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
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
        tool_callable = convert_to_function(cleaned_data.get("tool_code"))
        try:
            schema = generate_schema(tool_callable)
            context_params = [param for param in schema["parameters"]["required"] if param.startswith('__') and param.endswith('__')]

            # Filter out parameters with names in the format __{name}__
            required_params = [param for param in schema["parameters"]["required"] if not param.startswith('__') and not param.endswith('__')]
            required_properties = {param: schema["parameters"]["properties"][param] for param in required_params}

            schema["parameters"]["properties"] = required_properties
            schema["parameters"]["required"] = required_params
            cleaned_data["tool_json_spec"] = schema
            cleaned_data["context_params"] = context_params
        except Exception as e:
            raise ValidationError({'tool_code': str(e)})

        return cleaned_data

class ToolAdmin(admin.ModelAdmin):
    form = ToolAdminForm

class MyJSONDecoder(json.JSONDecoder):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,strict=False)
#


class ConversationWidget(forms.Textarea):

    def format_value(self, value):
        # Convert JSON to string format for display
        if value is None:
            return ''
        conversation_text = []
        for item in value:
            role = item.get('role', '')
            content = item.get('content', '').replace('\n', '\n')
            conversation_text.append(f"__{role}__:{content}")
        return '\n'.join(conversation_text)


class ConversationField(forms.CharField):
    widget = ConversationWidget

    def to_python(self, value):
        # Convert string from form to Python list of dicts (JSON)
        lines = value.split('\n')
        result = []
        current_role = None
        current_content = []

        for line in lines:
            if line.startswith('__user__:') or line.startswith('__assistant__:'):
                if current_role and current_content:
                    result.append({'role': current_role, 'content': '\n'.join(current_content).strip()})
                current_role = 'user' if 'user' in line else 'assistant'
                current_content = [line.split(':', 1)[1].strip()]
            else:
                current_content.append(line)

        if current_role and current_content:
            result.append({'role': current_role, 'content': '\n'.join(current_content).strip()})
        return result

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.widget.format_value(value)



class PromptTemplateAdminForm(forms.ModelForm):
    llm_config_name = forms.ChoiceField(required=True)
    # initial_messages_templates = MyJSONField(decoder=MyJSONDecoder)
    initial_messages_templates = ConversationField(help_text="Write msgs in format __user__:<Text> __assistant__:<Text>")
    class Meta:
        model = PromptTemplate
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PromptTemplateAdminForm, self).__init__(*args, **kwargs)
        # Dynamically generate choices
        dynamic_choices = self.get_dynamic_choices()
        self.fields['llm_config_name'].choices = dynamic_choices

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def get_dynamic_choices(self):
        return [(key,key) for key in GLOBAL_LOADED_LLM_CONFIGS.keys()]


class PromptTemplateAdmin(admin.ModelAdmin):
    form = PromptTemplateAdminForm
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

# Sanchit - TODO -  Always declare admin of models, for easier creation and reference/debug, unless deciding explicitly against or in
# in case of through models

admin.site.register(OpenAIAssistant, OpenAIAssistantAdmin)
admin.site.register(ChatHistory)
admin.site.register(KnowledgeRepository)
admin.site.register(ContentReference)
admin.site.register(PromptTemplate, PromptTemplateAdmin)
admin.site.register(Tool, ToolAdmin)
