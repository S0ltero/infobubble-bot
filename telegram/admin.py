from django.contrib import admin
from .models import TelegramUser, TelegramChannel, UserMessageRate

from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from import_export.fields import Field

admin.site.register(TelegramUser)
admin.site.register(UserMessageRate)

class TelegramChannelResource(resources.ModelResource):
    channel_id = Field(attribute='channel_id', column_name='channel_id')

    class Meta:
        model = TelegramChannel
        fields = "__all__"


@admin.register(TelegramChannel)
class AdminUser(ImportExportActionModelAdmin):
    resource_class = TelegramChannelResource
    actions = None