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
        try:
            os.remove(os.path.join(settings.MEDIA_ROOT, instance.file.name))
        except (FileNotFoundError, IsADirectoryError):
            pass
        instance.file = None
        instance.has_file = False
        instance.save()

    logger.info(f"Удалено {len(queryset)} файлов")
