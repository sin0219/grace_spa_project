from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # 3ステップ予約フォーム
    path('booking/step1/', views.booking_step1, name='booking_step1'),  # サービス選択
    path('booking/step2/', views.booking_step2, name='booking_step2'),  # 日時・施術者選択
    path('booking/step3/', views.booking_step3, name='booking_step3'),  # お客様情報入力
    path('booking/confirm/', views.booking_confirm, name='booking_confirm'),  # 確認画面
    path('booking/complete/', views.booking_complete, name='booking_complete'),  # 完了画面
    
   
    # AJAX API
    path('api/available-times/', views.get_available_times, name='get_available_times'),
]