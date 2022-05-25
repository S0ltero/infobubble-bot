import os

from django.conf import settings
from django.utils import timezone

from celery.utils.log import get_task_logger

from project.celery import app
from .models import TelegramMessage

logger = get_task_logger(__name__)

@app.task
def clear_files():
    date = timezone.now() - timezone.timedelta(days=1)
    queryset = TelegramMessage.objects.filter(date__lte=date, has_file=True)

    for instance in queryset:
        if not os.path.exists(instance.file.path):
            print("File not found")
            continue
        instance.file.delete()
        instance.has_file = False
        instance.archived = True
        instance.save()

    logger.info(f"Удалено {len(queryset)} файлов")
