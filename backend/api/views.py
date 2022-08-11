from django.db.utils import IntegrityError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.generics import ListAPIView

from telegram.models import TelegramChannel, TelegramMessage, TelegramUser, HistoryMessage, UserSubscribe, Config
from telegram.serializers import (
    TelegramUserSerializer,
    TelegramChannelSerializer,
    TelegramMessageSerializer,
    HistoryMessageSerializer,
    UserMessageRateSerializer,
    UserSubscribeSerializer,
    ConfigSerializer
)


class UserViewset(viewsets.GenericViewSet):
    queryset = TelegramUser
    serializer_class =TelegramUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        tags = self.request.query_params.get("tags")
        if tags:
            qs = qs.filter(filters__overlap=tags)

    def retrieve(self, request, pk=None):
        try:
            user = self.queryset.objects.get(id=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        data = request.data

        try:
            user = TelegramUser.objects.get(id=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(instance=user, data=data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.update(user, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        try:
            tags = self.request.query_params.get("tags")
            if tags:
                tags = tags.split(",")
                users = self.queryset.objects.filter(filters__overlap=tags)
            else:
                users = self.queryset.objects.all()
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            user = self.queryset.objects.get(id=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def news(self, request, pk=None):
        try:
            user = self.queryset.objects.get(pk=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        news = TelegramMessage.objects.filter(channel__tags__overlap=user.filters)
        news = news.exclude(history__user_id=user.id)
        for word in user.filter_words:
            news.exclude(text__contains=word)
        news = news[:50]

        serializer = TelegramMessageSerializer(news, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_name="news-subscribe", url_path="news-subscribe")
    def news_subscribe(self, request, pk=None):
        try:
            user = self.queryset.objects.prefetch_related("subscribes").get(id=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        subscribes = user.subscribes.values_list("channel_id", flat=True)

        news = TelegramMessage.objects.filter(channel__in=subscribes)
        news = news.exclude(history__user_id=user.id)[:50]

        serializer = TelegramMessageSerializer(news, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChannelViewset(viewsets.GenericViewSet):
    queryset = TelegramChannel
    serializer_class = TelegramChannelSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        tags = self.request.query_params.get("tags")
        if tags:
            qs = qs.objects.filter(tags__overlap=tags)

        return qs

    def retrieve(self, request, pk=None):
        try:
            channel = self.queryset.objects.get(channel_id=pk)
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(channel)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        data = request.data

        try:
            channel = self.queryset.objects.get(channel_url=pk)
        except TelegramChannel.DoesNotExist:
            return Response(f'Канал с url: {pk} не найден', status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(channel, data=data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.update(channel, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        tags = self.request.query_params.get("tags")

        try:
            if tags:
                tags = tags.split(",")
                channels = self.queryset.objects.filter(tags__overlap=tags)
            else:
                channels = self.queryset.objects.all()
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        channels = channels.values_list("channel_url", "channel_id")
        return Response(channels, status=status.HTTP_200_OK)

    @action(detail=True)
    def subscribes(self, request, pk=None):
        try:
            channel = self.queryset.objects.get(channel_id=pk)
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(channel)
        return Response(serializer.data["subscribes"], status=status.HTTP_200_OK)


class MessageViewset(viewsets.GenericViewSet):
    queryset = TelegramMessage
    serializer_class = TelegramMessageSerializer

    def retrieve(self, request, pk=None):
        try:
            message = self.queryset.objects.get(id=pk)
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(message)
        return Response(serializer.data["subscribes"], status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            try:
                serializer.save()
            except IntegrityError:
                return Response("Данное сообщение уже существует", status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            message = self.queryset.objects.get(id=pk)
        except TelegramMessage.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        message.delete()
        return Response(status=status.HTTP_200_OK)


class HistoryViewset(viewsets.GenericViewSet):
    queryset = HistoryMessage
    serializer_class = HistoryMessageSerializer

    @action(methods=["get"], detail=False, url_path=r"(?P<user_id>[\w-]+)/(?P<channel_id>[\w-]+)/(?P<message_id>[\w-]+)", url_name="list")
    def get_message(self, request, user_id, channel_id, message_id):
        try:
            history_message = self.queryset.objects.get(user_id=user_id, channel_id=channel_id, message_id=message_id)
        except HistoryMessage.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(history_message)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
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