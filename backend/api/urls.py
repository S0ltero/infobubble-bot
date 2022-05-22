from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from .views import *

app_name = 'api'

router = DefaultRouter()
router.register(r"channels", ChannelViewset, basename="channels")
router.register(r"users", UserViewset, basename="users")
router.register(r"messages", MessageViewset, basename="messages")
router.register(r"history", HistoryViewset, basename="history")

urlpatterns = [
    path('rate/', UserRateView.as_view()),
    path('subscribe/', UserSubscribeView.as_view()),
    path('subscribe/<channel_id>/<user_id>', UserSubscribeView.as_view()),
    path('config/', ConfigView.as_view())
] + router.urls