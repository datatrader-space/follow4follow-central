from rest_framework import serializers
from .models import Event, Server

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    server = serializers.PrimaryKeyRelatedField(queryset=Server.objects.all())

    class Meta:
        model = Event
        fields = '__all__'