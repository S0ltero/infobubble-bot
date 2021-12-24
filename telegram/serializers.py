from rest_framework import serializers

from .models import (
    TelegramUser,
    HistoryMessage,
)

class TelegramUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = TelegramUser
        fields = "__all__"


class HistoryMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = HistoryMessage
        fields = "__all__"
