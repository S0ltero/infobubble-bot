from django.contrib.postgres.fields import ArrayField
from django.db import models


class TelegramUser(models.Model):
    user_id = models.CharField(verbose_name="ID telegram пользователя", max_length=130)
    filters = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Пользовательские фильтры')
    filter_words = ArrayField(models.CharField(max_length=150), blank=True, verbose_name="Слова фильтры")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class TelegramChannel(models.Model):
    channel_id = models.CharField(verbose_name="ID telegram канала", max_length=130)
    tags = ArrayField(models.CharField(max_length=150), blank=True, verbose_name='Тэги канала')

    def __str__(self):
       return f"{self.channel_id}"


    class Meta:
        verbose_name = "Канал"
        verbose_name_plural = "Каналы"


class HistoryMessage(models.Model):
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel_id = models.CharField(verbose_name='ID канала', max_length=130)
    user_id = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Собщение истории"
        verbose_name_plural = "Собщения истории"


class UserMessageRate(models.Model):
    message_id = models.CharField(verbose_name="ID сообщения", max_length=130)
    channel_id = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE)
    user_id = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    rate = models.BooleanField(verbose_name="Оценка сообщения")

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"