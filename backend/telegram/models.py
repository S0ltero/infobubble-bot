from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint


def validate_channel_url(value: str):
    """Check if channel url is valid for Telegram use"""
    if not value.startswith('@'):
        raise ValidationError(
            f'{value} is not @username of telegram channel',
            params={'value': value}
        )


class TelegramUser(models.Model):
    id = models.CharField(verbose_name="ID telegram пользователя", max_length=130, unique=True, primary_key=True)
    filters = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Пользовательские фильтры')
    filter_words = ArrayField(models.CharField(max_length=150), blank=True, default=list, verbose_name="Слова фильтры")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class TelegramChannel(models.Model):
    """Represent channel of Telegram"""
    channel_id = models.CharField(
        verbose_name="ID telegram канала",
        max_length=130,
        unique=True,
        blank=True,
        null=True
    )
    channel_url = models.CharField(
        verbose_name="Ссылка на канал",
        max_length=130,
        unique=True,
        blank=True,
        help_text='Пример: @testchannel',
        validators=(validate_channel_url,)
    )
    title = models.CharField(verbose_name="Название канала", max_length=130)
    tags = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Тэги канала')

    class Meta:
        verbose_name = "Канал"
        verbose_name_plural = "Каналы"

    def __str__(self) -> str:
        return f"{self.channel_url}"


class TelegramMessage(models.Model):
    """Represetn message of Telegram"""
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel = models.ForeignKey(TelegramChannel, verbose_name="Канал сообщения", to_field="channel_id", on_delete=models.CASCADE)
    text = models.TextField(verbose_name="Текст сообщения", max_length=4096, blank=True)
    date = models.DateField(verbose_name="Дата создания", auto_now_add=True)
    media_group_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        unique_together = ("message_id", "channel_id")
        indexes = (
            models.Index(fields=["message_id", "channel", "date"]),
        )


class TelegramMedia(models.Model):
    """Represent media files of Telegram"""

    class Type(models.TextChoices):
        AUDIO = "AUDIO"
        DOCUMENT = "DOCUMENT"
        PHOTO = "PHOTO"
        STICKER = "STICKER"
        VIDEO = "VIDEO"
        ANIMATION = "ANIMATION"
        VOICE = "VOICE"
        VIDEO_NOTE = "VIDEO_NOTE"
        CONTACT = "CONTACT"
        LOCATION = "LOCATION"
        WEB_PAGE = "WEB_PAGE"

    message = models.ForeignKey(TelegramMessage, related_name="media", on_delete=models.CASCADE)
    media_group_id = models.CharField(max_length=255, blank=True, null=True)
    file_id = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=Type.choices)

    class Meta:
        verbose_name = "Медиа файл"
        verbose_name_plural = "Медиа файлы"
        constraints = (
            UniqueConstraint(
                fields=("file_id",),
                condition=Q(media_group_id=None),
                name="unique_without_media_group"
            ),
            UniqueConstraint(
                fields=("media_group_id", "file_id"),
                name="unique_with_media_group"
            ),
        )


class HistoryMessage(models.Model):
    message = models.ForeignKey(TelegramMessage, related_name="history", on_delete=models.PROTECT)
    user = models.ForeignKey(TelegramUser, related_name="history", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Собщение истории"
        verbose_name_plural = "Собщения истории"


class UserMessageRate(models.Model):
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel_id = models.ForeignKey(TelegramChannel, related_name="rate", to_field="channel_id", on_delete=models.CASCADE)
    user_id = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    rate = models.BooleanField(verbose_name="Оценка сообщения")

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"
        unique_together = ("message_id", "channel_id", "user_id")


class UserSubscribe(models.Model):
    user = models.ForeignKey(TelegramUser, related_name="subscribes", on_delete=models.CASCADE)
    channel = models.ForeignKey(TelegramChannel, related_name="subscribes", to_field="channel_id", on_delete=models.CASCADE)


class Config(models.Model):
    last_sent = models.DateField(verbose_name='Дата последнего напоминания', default=timezone.now)

    class Meta:
        verbose_name = 'Настройка'
        verbose_name_plural = 'Настройки'