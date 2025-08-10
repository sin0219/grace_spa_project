from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='home'),
    path('dashboard/bookings/', views.booking_list, name='booking_list'),
    path('dashboard/booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('dashboard/customers/', views.customer_list, name='customer_list'),
    path('dashboard/calendar/', views.calendar_view, name='calendar'),
    path('dashboard/week/', views.week_view, name='week_calendar'),
]