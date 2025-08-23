from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    # 日本語版（既存）
    path('', views.home, name='home'),
    path('therapists/', views.therapists, name='therapists'),
    
    # ★ 英語版URL追加
    path('en/', views.home_en, name='home_en'),
    path('en/therapists/', views.therapists_en, name='therapists_en'),
]
