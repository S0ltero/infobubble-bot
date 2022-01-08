from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from telegram.models import TelegramChannel, TelegramUser, HistoryMessage
from telegram.serializers import (
    TelegramUserSerializer,
    HistoryMessageSerializer,
    UserMessageRateSerializer
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

    def get(self, request):
        channel_ids = self.queryset.objects.values_list("id", flat=True)

        if channel_ids:
            return Response({'channels_ids': channel_ids}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        data = request.data

        if data.get('tags'):
            tags = data['tags']
            channel_ids = TelegramChannel.objects.filter(tags__overlap=tags).values_list("id", flat=True)

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
