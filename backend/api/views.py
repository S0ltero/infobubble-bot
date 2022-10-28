import operator
from functools import reduce

from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import viewsets

from telegram.models import TelegramChannel, TelegramMessage, TelegramUser, HistoryMessage, UserSubscribe, Config
from telegram.serializers import (
    TelegramUserSerializer,
    TelegramChannelSerializer,
    TelegramMessageSerializer,
    TelegramMediaSerializer,
    HistoryMessageSerializer,
    UserMessageRateSerializer,
    UserSubscribeSerializer,
    ConfigSerializer
)


class UserViewset(viewsets.GenericViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        tags = self.request.query_params.get("tags")
        if tags:
            qs = qs.filter(filters__overlap=tags)

        return qs

    def retrieve(self, request, pk=None):
        user = self.get_object()
        serializer = self.serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        user = self.get_object()
        serializer = self.serializer_class(instance=user, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.update(user, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        users = self.get_queryset()
        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def news(self, request, pk=None):
        user = self.get_object()

        query = [
            ~Q(history__in=user.history.all()) &
            Q(date__gte=timezone.now().replace(hour=0, minute=0, second=0)) &
            Q(channel__tags__overlap=user.filters)
        ]

        if user.filter_words:
            query.append(
                reduce(
                    operator.and_, [~Q(text__icontains=s) for s in user.filter_words]
                )
            )

        news = TelegramMessage.objects.filter(*query)[:50]

        serializer = TelegramMessageSerializer(news, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_name="news-subscribe", url_path="news-subscribe")
    def news_subscribe(self, request, pk=None):
        try:
            qs = self.get_queryset()
            user = qs.prefetch_related("subscribes").get(id=pk)
        except TelegramUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        subscribes = user.subscribes.values_list("channel_id", flat=True)

        news = TelegramMessage.objects.filter(channel__in=subscribes)
        news = news.exclude(history__user_id=user.id)[:50]

        serializer = TelegramMessageSerializer(news, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChannelViewset(viewsets.GenericViewSet):
    queryset = TelegramChannel.objects.all()
    serializer_class = TelegramChannelSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        tags = self.request.query_params.get("tags")
        if tags:
            qs = qs.objects.filter(tags__overlap=tags)

        return qs

    def retrieve(self, request, pk=None):
        channel = self.get_object()
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
        channel = self.get_object()
        serializer = self.serializer_class(channel, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.update(channel, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        channels = self.get_queryset()
        channels = channels.values_list("channel_url", "channel_id")
        return Response(channels, status=status.HTTP_200_OK)

    @action(detail=False, url_name="ids", url_path="ids")
    def ids(self, request):
        qs = self.get_queryset()
        channel_ids = qs.values_list("channel_id", flat=True)
        return Response(channel_ids, status=status.HTTP_200_OK)


    @action(detail=True)
    def subscribes(self, request, pk=None):
        try:
            channel = self.queryset.objects.get(channel_id=pk)
        except TelegramChannel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(channel)
        return Response(serializer.data["subscribes"], status=status.HTTP_200_OK)


class MessageViewset(viewsets.GenericViewSet):
    queryset = TelegramMessage.objects.all()
    serializer_class = TelegramMessageSerializer

    def retrieve(self, request, pk=None):
        message = self.get_queryset()
        serializer = self.serializer_class(message)
        return Response(serializer.data["subscribes"], status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
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

    @action(
        detail=False,
        methods=["post"],
        url_name="media",
        url_path=r"(?P<channel_id>[\w-]+)/(?P<message_id>[\w-]+)/media",
        serializer_class=TelegramMediaSerializer
    )
    def media(self, request, channel_id, message_id):
        """Add media file id to `TelegramMessage` by `channel_id` and `message_id`"""
        qs = self.get_queryset()
        message = get_object_or_404(qs, channel_id=channel_id, message_id=message_id)
        serializer = self.serializer_class(data=request.data, many=True)
        if serializer.is_valid(raise_exception=False):
            serializer.save(message_id=message.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        url_name="media-group",
        url_path=r"media/(?P<media_group_id>[\w-]+)",
        serializer_class=TelegramMediaSerializer
    )
    def media_group(self, request, media_group_id):
        """Add group of media files ids to `TelegramMessage` by `channel_id` and `media_group_id`"""
        qs = self.get_queryset()
        message = get_object_or_404(qs, media_group_id=media_group_id)
        serializer = self.serializer_class(data=request.data, many=True)
        if serializer.is_valid(raise_exception=False):
            serializer.save(message_id=message.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HistoryViewset(viewsets.GenericViewSet):
    queryset = HistoryMessage.objects.all()
    serializer_class = HistoryMessageSerializer

    @action(methods=["get"], detail=False, url_path=r"(?P<user_id>[\w-]+)/(?P<channel_id>[\w-]+)/(?P<message_id>[\w-]+)", url_name="list")
    def get_message(self, request, user_id, channel_id, message_id):
        qs = self.get_queryset()
        history_message = get_object_or_404(qs, user_id=user_id, channel_id=channel_id, message_id=message_id)
        serializer = self.serializer_class(history_message)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRateView(APIView):
    serializer_class = UserMessageRateSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
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
        serializer = self.serializer_class(data=request.data)
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