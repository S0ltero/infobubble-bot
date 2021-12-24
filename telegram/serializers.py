from rest_framework import serializers

from .models import (
    TelegramUser,
    HistoryMessage,
    UserMessageRate
)


class TelegramUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = TelegramUser
        fields = "__all__"


class HistoryMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = HistoryMessage
        fields = "__all__"


class UserMessageRateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMessageRate
        fields = "__all__"