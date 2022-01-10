from rest_framework import serializers

from .models import (
    TelegramUser,
    TelegramChannel,
    HistoryMessage,
    UserMessageRate
)


class TelegramUserSerializer(serializers.ModelSerializer):
    channel_ids = serializers.SerializerMethodField()
    subscribe_ids = serializers.SerializerMethodField()

    class Meta:
        model = TelegramUser
        fields = "__all__"

    def get_channel_ids(self, obj):
        channel_ids = TelegramChannel.objects.filter(tags__overlap=obj.filters).values_list("id", flat=True)
        return channel_ids

    def get_subscribe_ids(self, obj):
        subscribe_ids = obj.subscribes.values_list("channel_id", flat=True)
        return subscribe_ids


class TelegramChannelSerializer(serializers.ModelSerializer):

    class Meta:
        model = TelegramChannel
        fields = "__all__"


class HistoryMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = HistoryMessage
        fields = "__all__"


class UserMessageRateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMessageRate
        fields = "__all__"