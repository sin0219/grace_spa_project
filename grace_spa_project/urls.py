from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),  # ← この行を追加
    path('', include('bookings.urls')),
    path('', include('dashboard.urls')), 
]