from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # 基本ページ
    path('dashboard/', views.dashboard_home, name='home'),
    path('dashboard/bookings/', views.booking_list, name='booking_list'),
    path('dashboard/booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('dashboard/customers/', views.customer_list, name='customer_list'),
    path('dashboard/calendar/', views.calendar_view, name='calendar'),
    path('dashboard/week/', views.week_view, name='week_calendar'),
    
    # 予約管理機能
    path('dashboard/booking/create/', views.booking_create_dashboard, name='booking_create'),
    
    # 予定管理機能
    path('dashboard/schedules/', views.schedule_list, name='schedule_list'),
    path('dashboard/schedule/create/', views.schedule_create, name='schedule_create'),
    path('dashboard/schedule/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('dashboard/schedule/<int:schedule_id>/delete/', views.schedule_delete, name='schedule_delete'),
    
    # API エンドポイント
    path('dashboard/api/available-times/', views.get_available_times_api, name='api_available_times'),
    path('dashboard/api/schedule-times/', views.get_schedule_times_api, name='api_schedule_times'),
]