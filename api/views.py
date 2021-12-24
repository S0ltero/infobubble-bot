import os
import json
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from telegram.models import TelegramChannel, TelegramUser, HistoryMessage, UserMessageRate

from telegram.serializers import (
    TelegramUserSerializer,
    HistoryMessageSerializer,
    UserMessageRateSerializer
)


def validate_token(token):
    home = Path(__file__).resolve().parent.parent
    with open(os.path.join(home, 'local', 'config.json')) as file:
        config = json.load(file)
    return token == config.get('token')


class UserView(APIView):
    queryset = TelegramUser
    serializer_class = TelegramUserSerializer

    def get(self, request):
        try:
            users = self.queryset.objects.all()
        except TelegramUser.DoesNotExist:
            return Response(
                data={"description": "Пользователи не найдены", 
                      "error": "users_not_found"}, 
                status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        if not validate_token(data['token']):
            return Response(status=404)

        try:
            user = TelegramUser.objects.get(user_id=data.get('user_id'))
        except TelegramUser.DoesNotExist:
            if data.get('user_id') and data.get('filters'):
                user = TelegramUser()
                user.user_id = data['user_id']
                user.filters = data['filters']
            else:
                return Response(status=204)

        if data.get('filters'):
            user.filters = data.get('filters')
            user.save()
            return Response(status=200)
        else:
            return Response({
                'user_id': user.id,
                'filters': user.filters
            })


class ChannelView(APIView):

    def post(self, request):
        data = request.data

        if not validate_token(data['token']):
            return Response(status=404)

        if not data.get('tags'):
            channels = TelegramChannel.objects.all()
            channels = tuple(x.channel_id for x in channels)
        else:
            tags = data['tags']
            channels = TelegramChannel.objects.filter(tags__overlap=tags)
            channels = tuple(x.channel_id for x in channels)

        if channels:
            return Response({
                'channels_ids': channels
            })
        else:
            return Response(status=204)


class HistoryMessageView(APIView):

    def post(self, request):
        data = request.data

        if not validate_token(data['token']):
            return Response(status=404)

        message_id = data.get('message_id')
        channel_id = data.get('channel_id')
        user_id = data.get('user_id')

        user = TelegramUser.objects.get(user_id=user_id)

        history_message = HistoryMessage()
        history_message.message_id = message_id
        history_message.channel_id = channel_id
        history_message.user_id =user

        history_message.save()

        return Response(status=200)


class UserRateView(APIView):

    def post(self, request):
        data = request.data

        if not validate_token(data['token']):
            return Response(status=404)

        message_id = data.get('message_id')
        channel_id = data.get('channel_id')
        user_id = data.get('user_id')
        rate = data.get('rate')

        channel = TelegramChannel.objects.get(channel_id=channel_id)
        user = TelegramUser.objects.get(user_id=user_id)

        user_rate = UserMessageRate()
        user_rate.message_id = message_id
        user_rate.channel_id = channel
        user_rate.user_id = user
        user_rate.rate = rate

        user_rate.save()

        return Response(status=200)
