from django.contrib import admin
from .models import (
    TelegramUser, TelegramChannel,
    TelegramMessage, TelegramMedia,
    UserMessageRate, UserSubscribe,
    HistoryMessage, Config)

from import_export import resources
from import_export.admin import ImportExportActionModelAdmin

admin.site.register(TelegramUser)
admin.site.register(UserMessageRate)
admin.site.register(UserSubscribe)
admin.site.register(HistoryMessage)
admin.site.register(Config)
admin.site.register(TelegramMessage)
admin.site.register(TelegramMedia)

class TelegramChannelResource(resources.ModelResource):

    class Meta:
        model = TelegramChannel
        fields = "__all__"


@admin.register(TelegramChannel)
class AdminUser(ImportExportActionModelAdmin):
    resource_class = TelegramChannelResource
    actions = None