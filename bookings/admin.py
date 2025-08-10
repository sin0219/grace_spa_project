from django.contrib import admin
from .models import Service, Customer, Booking, Therapist, BusinessHours, BookingSettings

@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'experience_years', 'is_active', 'is_featured', 'sort_order', 'total_bookings']
    list_filter = ['is_active', 'is_featured', 'experience_years']
    search_fields = ['name', 'display_name']
    list_editable = ['is_active', 'is_featured', 'sort_order']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'display_name')  # photo は一時的にコメントアウト
        }),
        ('プロフィール', {
            'fields': ('introduction', 'specialties', 'experience_years')
        }),
        ('表示設定', {
            'fields': ('is_active', 'is_featured', 'sort_order')
        })
    )
    
    def total_bookings(self, obj):
        return obj.total_bookings
    total_bookings.short_description = '総予約数'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_minutes', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['customer', 'service', 'therapist', 'booking_date', 'booking_time', 'status', 'created_at']
    list_filter = ['status', 'booking_date', 'service', 'therapist']
    search_fields = ['customer__name', 'customer__email']
    list_editable = ['status']
    date_hierarchy = 'booking_date'
    
    fieldsets = (
        ('予約情報', {
            'fields': ('customer', 'service', 'therapist', 'booking_date', 'booking_time', 'status')
        }),
        ('備考', {
            'fields': ('notes',)
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ['weekday_display', 'is_open', 'open_time', 'close_time', 'last_booking_time']
    list_filter = ['is_open']
    list_editable = ['is_open', 'open_time', 'close_time', 'last_booking_time']
    ordering = ['weekday']
    
    def weekday_display(self, obj):
        return dict(BusinessHours.WEEKDAY_CHOICES)[obj.weekday]
    weekday_display.short_description = '曜日'

@admin.register(BookingSettings)
class BookingSettingsAdmin(admin.ModelAdmin):
    list_display = ['booking_interval_minutes', 'advance_booking_days', 'default_treatment_duration', 'updated_at']
    
    def has_add_permission(self, request):
        # 設定は1つだけしか作成できないようにする
        return not BookingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 設定は削除できないようにする
        return False    