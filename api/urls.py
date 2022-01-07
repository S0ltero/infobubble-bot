from django.urls import path, re_path

from .views import *

app_name = 'api'

urlpatterns = [
    path('user/', UserView.as_view()),
    path('user/<user_id>', UserView.as_view()),
    path('users/', UserListView.as_view()),
    path('channels/', ChannelView.as_view()),
    path('rate/', UserRateView.as_view())
]