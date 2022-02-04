from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from telegram.models import TelegramChannel, TelegramUser, HistoryMessage, UserSubscribe, Config
from telegram.serializers import (
    TelegramUserSerializer,
    TelegramChannelSerializer,
    HistoryMessageSerializer,
    UserMessageRateSerializer,
    UserSubscribeSerializer,
    ConfigSerializer
)


class UserView(APIView):
    queryset = TelegramUser
    serializer_class = TelegramUserSerializer

    def get(self, request, user_id):
        try:
            user = self.queryset.objects.get(id=user_id)
        except TelegramUser.DoesNotExist:
            return Response(
                data={"description": "Пользователь не найден", 
                      "error": "user_not_found"}, 
                status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        data = request.data

        try:
            user = TelegramUser.objects.get(id=data["id"])
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


class UserListView(ListAPIView):
    queryset = TelegramUser
    serializer_class = TelegramUserSerializer

    def get(self, request, *args, **kwargs):
        try:
            users = TelegramUser.objects.all()
        except TelegramUser.DoesNotExist:
            return Response(
                data={"description": "Пользователи не найдены", 
                      "error": "users_not_found"},
                status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChannelView(APIView):
    queryset = TelegramChannel
    serializer_class = TelegramChannelSerializer

    def get(self, request, channel_id):
        try:
            channel = self.queryset.objects.get(channel_id=channel_id)
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(channel)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        data = request.data

        try:
            channel = self.queryset.objects.get(channel_url=data['channel_url'])
        except TelegramChannel.DoesNotExist:
            return Response(f'Канал с url: {data["channel_url"]} не найден', status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(channel, data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.update(channel, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChannelsView(APIView):
    queryset = TelegramChannel

    def get(self, request):
        channel_ids = self.queryset.objects.values_list("channel_url", flat=True)

        if channel_ids:
            return Response({'channels_ids': channel_ids}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        data = request.data
        channel_ids = []

        if data.get('tags'):
            tags = data['tags']
            channel_ids = TelegramChannel.objects.filter(tags__overlap=tags).values_list("channel_id", flat=True)

        if channel_ids:
            return Response({'channels_ids': channel_ids}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class HistoryMessageView(APIView):
    queryset = HistoryMessage
    serializer_class = HistoryMessageSerializer

    def get(self, request, user_id, channel_id, message_id):
        try:
            history_message = self.queryset.objects.get(user_id=user_id, channel_id=channel_id, message_id=message_id)
        except HistoryMessage.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(history_message)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRateView(APIView):
    serializer_class = UserMessageRateSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSubscribeView(APIView):
    queryset = UserSubscribe
    serializer_class = UserSubscribeSerializer

    def get(self, request, channel_id, user_id):
        try:
            subscribe = self.queryset.objects.get(channel_id=channel_id, user_id=user_id)
        except UserSubscribe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serialzer = self.serializer_class(subscribe)
        return Response(serialzer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, channel_id, user_id):
        try:
            subscribe = self.queryset.objects.get(channel_id=channel_id, user_id=user_id)
        except UserSubscribe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfigView(APIView):
    queryset = Config
    serializer_class = ConfigSerializer

    def get(self, request):
        config, created = self.queryset.objects.get_or_create(id=0)
        serializer = self.serializer_class(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        data = request.data
        config = self.queryset.objects.first()

        serializer = self.serializer_class(config, data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.update(config, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)