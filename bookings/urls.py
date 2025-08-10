from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('booking/', views.booking_create, name='booking_create'),
    path('booking/success/<int:booking_id>/', views.booking_success, name='booking_success'),
]