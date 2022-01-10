from django.urls import path, re_path

from .views import *

app_name = 'api'

urlpatterns = [
    path('user/', UserView.as_view()),
    path('user/<user_id>', UserView.as_view()),
    path('users/', UserListView.as_view()),
    path('channel/', ChannelView.as_view()),
    path('channel/<channel_id>', ChannelView.as_view()),
    path('channels/', ChannelsView.as_view()),
    path('rate/', UserRateView.as_view()),
    path('subscribe/', UserSubscribeView.as_view()),
    path('history/', HistoryMessageView.as_view()),
    path('history/<user_id>/<channel_id>/<message_id>', HistoryMessageView.as_view())
]