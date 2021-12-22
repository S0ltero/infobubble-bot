from django.urls import path

from .views import *

app_name = 'api'

urlpatterns = [
    path('users/', UserView.as_view()),
    path('channels/', ChannelView.as_view()),
    path('rate/', UserRateView.as_view())
]