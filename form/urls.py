from django.urls import path, re_path

from . import views

app_name = 'form'

urlpatterns = [
    # ex: /
    path('', views.search, name='home'),
    path('search', views.search, name='search'),
    path('dashboard', views.dashboard, name='dashboard'),

]