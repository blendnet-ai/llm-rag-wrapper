# Generated by Django 4.2.14 on 2024-09-06 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('OpenAIService', '0002_alter_openaiassistant_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('chat_history', models.JSONField(default=list)),
            ],
        ),
        migrations.CreateModel(
            name='Tool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tool_code', models.TextField()),
                ('default_values_for_non_llm_params', models.JSONField(blank=True, default=dict)),
                ('tool_json_spec', models.JSONField(blank=True, default=dict)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('llm_config_name', models.CharField(max_length=100)),
                ('type', models.CharField(blank=True, max_length=100, null=True)),
                ('required_kwargs', models.JSONField(blank=True, default=list, help_text='Required key words to be passed in user prompt template. If not provided by calling code, error will be raised. AS OF NOW, ERROR IS RAISED IF ANY KEYWORD IS MISSED, SINCE OTHERWISE $TEMPLATE_VAR LIKE THING WILL REMAIN IN PROMPT. FOR REQUIRED_KEYWORD ARGUMENTS FUNCTIONALITY, WE NEED DEFAULT VALUES OF OPTIONAL ARGS. CHECK IF THIS IS NEEDED, OR REMOVE REQUIRED KWARGS FIELD FROM HERE.')),
                ('initial_messages_templates', models.JSONField(blank=True, default=list, help_text="Initial msgs in the format [{'role': 'assistant|user', 'content': '...'}]")),
                ('system_prompt_template', models.TextField()),
                ('user_prompt_template', models.TextField(blank=True, default='')),
                ('logged_context_vars', models.JSONField(blank=True, default=list, help_text='Context variables to be logged in the chat log along with each user message, for later analysis.')),
                ('tools', models.ManyToManyField(blank=True, to='OpenAIService.tool')),
            ],
        ),
    ]
