from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('', include('bookings.urls')),
    path('', include('dashboard.urls')),
    # emailsアプリはadmin経由でのみアクセス
]