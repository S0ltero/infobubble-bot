import os

from django.conf import settings
from rest_framework import serializers

from .models import (
    TelegramUser,
    TelegramChannel,
    TelegramMessage,
    TelegramMedia,
    HistoryMessage,
    UserMessageRate,
    UserSubscribe,
    Config
)


class TelegramUserSerializer(serializers.ModelSerializer):
    channel_ids = serializers.SerializerMethodField()
    subscribe_ids = serializers.SerializerMethodField()

    class Meta:
        model = TelegramUser
        fields = "__all__"

    def get_channel_ids(self, obj):
        channel_ids = TelegramChannel.objects.filter(tags__overlap=obj.filters).values_list("channel_id", flat=True)
        return channel_ids

    def get_subscribe_ids(self, obj):
        subscribe_ids = obj.subscribes.values_list("channel_id", flat=True)
        return subscribe_ids


class TelegramChannelSerializer(serializers.ModelSerializer):
    subscribes = serializers.SerializerMethodField()

    class Meta:
        model = TelegramChannel
        fields = "__all__"

    def get_subscribes(self, obj):
        return obj.subscribes.values_list("user_id", flat=True)


class TelegramMediaSerializer(serializers.ModelSerializer):

    class Meta:
        model = TelegramMedia
        fields = "__all__"
        extra_kwargs = {"message": {"required": False}}


class TelegramMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = TelegramMessage
        fields = "__all__"


class HistoryMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = HistoryMessage
        fields = "__all__"


class UserMessageRateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMessageRate
        fields = "__all__"


class UserSubscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSubscribe
        fields = "__all__"


class ConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = Config
        fields = "__all__"