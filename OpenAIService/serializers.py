from rest_framework import serializers
from .models import OpenAIAssistant,KnowledgeRepository, ContentReference

class OpenAIAssistantSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenAIAssistant
        fields = ['id', 'assistant_id', 'name', 'instructions', 'open_ai_model', 'tools']


class KnowledgeRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeRepository
        fields = '__all__' 

class ContentReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentReference
        fields = '__all__'
