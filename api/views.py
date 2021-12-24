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
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        data = request.data

        try:
            user = TelegramUser.objects.get(pk=data["user_id"])
        except TelegramUser.DoesNotExist:
            return Response(
                data={"description": "Пользователь не найден", 
                      "error": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(instance=user, data=data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.update(user, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChannelView(APIView):
    queryset = TelegramChannel

    def post(self, request):
        data = request.data

        if not validate_token(data['token']):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        if not data.get('tags'):
            channel_ids = self.queryset.objects.values_list("channel_id", flat=True)
        else:
            tags = data['tags']
            channel_ids = TelegramChannel.objects.filter(tags__overlap=tags).values_list("channel_id", flat=True)

        if channel_ids:
            return Response({'channels_ids': channel_ids}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


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
