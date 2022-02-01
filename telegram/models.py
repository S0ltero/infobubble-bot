from django.contrib.postgres.fields import ArrayField
from django.db import models


class TelegramUser(models.Model):
    id = models.CharField(verbose_name="ID telegram пользователя", max_length=130, unique=True, primary_key=True)
    filters = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Пользовательские фильтры')
    filter_words = ArrayField(models.CharField(max_length=150), blank=True, null=True, verbose_name="Слова фильтры")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class TelegramChannel(models.Model):
    channel_id = models.CharField(verbose_name="ID telegram канала", max_length=130, null=True, blank=True)
    channel_url = models.CharField(verbose_name="Ссылка на канал", max_length=130, null=True, blank=True)
    title = models.CharField(verbose_name="Название канала", max_length=130, null=True, blank=True)
    tags = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Тэги канала')

    class Meta:
        verbose_name = "Канал"
        verbose_name_plural = "Каналы"


class HistoryMessage(models.Model):
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel_id = models.ForeignKey(TelegramChannel, related_name="history", to_field='channel_id', on_delete=models.CASCADE)
    user_id = models.ForeignKey(TelegramUser, related_name="history", on_delete=models.CASCADE)
    text = models.TextField(verbose_name="Текст сообщения")
    has_file = models.BooleanField(verbose_name="Содержит файл?")

    class Meta:
        verbose_name = "Собщение истории"
        verbose_name_plural = "Собщения истории"
        unique_together = ('message_id', 'channel_id', 'user_id')


class UserMessageRate(models.Model):
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel_id = models.ForeignKey(TelegramChannel, related_name="rate", to_field="channel_id", on_delete=models.CASCADE)
    user_id = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    rate = models.BooleanField(verbose_name="Оценка сообщения")

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"


class UserSubscribe(models.Model):
    user_id = models.ForeignKey(TelegramUser, related_name="subscribes", on_delete=models.CASCADE)
    channel_id = models.ForeignKey(TelegramChannel, related_name="subscribes", on_delete=models.CASCADE)
