from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Service, Therapist, Customer, Booking, BusinessHours, BookingSettings, Schedule, GapBlock

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_minutes', 'price_formatted', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    
    def price_formatted(self, obj):
        return f'¥{obj.price:,}'
    price_formatted.short_description = '料金'

@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender_display', 'email', 'phone', 'booking_count_display', 'created_at']
    list_filter = ['gender', 'is_first_visit', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    # フィールドセットで性別と初回利用を編集可能にする
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'email', 'phone')
        }),
        ('属性情報', {
            'fields': ('gender', 'is_first_visit'),
            'description': '顧客の性別は予約時の選択を参考に手動で設定してください。'
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def gender_display(self, obj):
        """性別をアイコン付きで表示"""
        if obj.gender == 'male':
            return format_html('<span style="color: #007bff;">👨 男性</span>')
        elif obj.gender == 'female':
            return format_html('<span style="color: #e91e63;">👩 女性</span>')
        else:
            return format_html('<span style="color: #ccc;">👤 未設定</span>')
    gender_display.short_description = '性別'
    
    def booking_count_display(self, obj):
        count = obj.booking_count
        if count > 0:
            url = reverse('admin:bookings_booking_changelist') + f'?customer__id__exact={obj.id}'
            return format_html('<a href="{}">{} 件</a>', url, count)
        return '0 件'
    booking_count_display.short_description = '予約回数'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # 1. list_display に customer_gender_display を追加
    list_display = ['customer', 'service', 'therapist_display', 'booking_date', 'booking_time', 'customer_gender_display', 'status_display', 'created_at']
    
    # 2. list_filter に customer_gender, customer_is_first_visit を追加
    list_filter = ['status', 'customer_gender', 'customer_is_first_visit', 'booking_date', 'service', 'therapist']
    
    # 3. 既存のfieldsets に「予約時の顧客情報」セクションを追加
    fieldsets = (
        ('予約情報', {
            'fields': ('customer', 'service', 'therapist', 'booking_date', 'booking_time', 'status')
        }),
        ('予約時の顧客情報', {  # ← この部分だけ追加
            'fields': ('customer_gender', 'customer_is_first_visit'),
            'description': 'お客様が予約時に選択した情報です。'
        }),
        ('詳細', {  # ← 既存のまま
            'fields': ('notes',)
        }),
        ('システム情報', {  # ← 既存のまま
            'fields': ('created_at', 'updated_at', 'end_time'),
            'classes': ('collapse',)
        }),
    )
    
    # 4. customer_gender_display メソッドのみ追加（他は既存のまま）
    def customer_gender_display(self, obj):
        """予約時の性別選択を表示"""
        if obj.customer_gender == 'male':
            return format_html('<span style="color: #007bff;">👨</span>')
        elif obj.customer_gender == 'female':
            return format_html('<span style="color: #e91e63;">👩</span>')
        else:
            return format_html('<span style="color: #ccc;">-</span>')
    customer_gender_display.short_description = '性別'
    
    # 既存のメソッドはそのまま保持
    def therapist_display(self, obj):
        return obj.therapist.display_name if obj.therapist else "指名なし"
    therapist_display.short_description = '施術者'
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'green',
            'completed': 'blue',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'ステータス'
    
    actions = ['mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} 件の予約を確定しました。')
    mark_as_confirmed.short_description = '選択した予約を確定する'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} 件の予約を完了しました。')
    mark_as_completed.short_description = '選択した予約を完了する'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} 件の予約をキャンセルしました。')
    mark_as_cancelled.short_description = '選択した予約をキャンセルする'

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ['weekday_display', 'is_open_display', 'open_time', 'close_time', 'last_booking_time']
    list_editable = ['open_time', 'close_time', 'last_booking_time']  # is_openを削除（display関数のため編集不可）
    ordering = ['weekday']
    
    def weekday_display(self, obj):
        return obj.get_weekday_display()
    weekday_display.short_description = '曜日'
    
    def is_open_display(self, obj):
        if obj.is_open:
            return format_html('<span style="color: green; font-weight: bold;">営業</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">定休日</span>')
    is_open_display.short_description = '営業'
    
    def has_add_permission(self, request):
        # 7曜日分のレコードが既に存在する場合は追加を禁止
        return BusinessHours.objects.count() < 7
    
    def has_delete_permission(self, request, obj=None):
        return False  # 削除を禁止

@admin.register(BookingSettings)
class BookingSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('基本設定', {
            'fields': (
                'booking_interval_minutes',
                'treatment_buffer_minutes',
                'advance_booking_days',
                'same_day_booking_cutoff',
                'min_advance_minutes',  # ←追加
                'default_treatment_duration'
            )
        }),
        ('予約機能設定', {
            'fields': (
                'allow_same_time_bookings',
                'enable_therapist_selection'
            )
        }),
        ('空白時間自動ブロック設定', {
            'fields': (
                'auto_block_gaps',
                'minimum_gap_minutes',
                'gap_block_before_opening',
                'gap_block_between_bookings',
                'gap_block_after_closing'
            ),
            'description': '短い空白時間を自動的に予約不可にする機能の設定'
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # 既に設定が存在する場合は追加を禁止
        return not BookingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False  # 削除を禁止
    
    def response_change(self, request, obj):
        """設定変更後の処理"""
        if obj.auto_block_gaps:
            try:
                obj.refresh_gap_blocks()
                messages.success(request, '予約設定を更新し、空白時間ブロックを再計算しました。')
            except Exception as e:
                messages.warning(request, f'設定は更新されましたが、ブロック再計算でエラーが発生しました: {str(e)}')
        else:
            # 自動ブロックが無効になった場合は既存の自動ブロックを無効化
            GapBlock.objects.filter(is_auto_generated=True, is_active=True).update(is_active=False)
            messages.success(request, '予約設定を更新し、自動生成されたブロックを無効化しました。')
        
        return super().response_change(request, obj)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['title', 'schedule_type_display', 'therapist_display', 'schedule_date', 'time_range', 'is_active']
    list_filter = ['schedule_type', 'is_active', 'schedule_date', 'therapist']
    search_fields = ['title', 'description']
    date_hierarchy = 'schedule_date'
    ordering = ['-schedule_date', 'start_time']
    list_editable = ['is_active']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('title', 'schedule_type', 'therapist')
        }),
        ('日時設定', {
            'fields': ('schedule_date', 'start_time', 'end_time')
        }),
        ('オプション', {
            'fields': ('description', 'is_recurring', 'is_active')
        }),
        ('システム情報', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def schedule_type_display(self, obj):
        colors = {
            'break': 'green',
            'meeting': 'blue',
            'training': 'orange',
            'maintenance': 'red',
            'preparation': 'purple',
            'admin': 'gray',
            'other': 'black',
        }
        color = colors.get(obj.schedule_type, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_schedule_type_display()
        )
    schedule_type_display.short_description = '予定種別'
    
    def therapist_display(self, obj):
        return obj.therapist.display_name if obj.therapist else "全体"
    therapist_display.short_description = '担当者'
    
    def time_range(self, obj):
        return f'{obj.start_time} - {obj.end_time}'
    time_range.short_description = '時間'

@admin.register(GapBlock)
class GapBlockAdmin(admin.ModelAdmin):
    list_display = [
        'block_date', 
        'therapist_display', 
        'time_range', 
        'block_type_display', 
        'is_auto_generated_display',
        'is_active',  # display関数ではなく実際のフィールドを使用
        'duration_display'
    ]
    list_filter = [
        'block_type', 
        'is_auto_generated', 
        'is_active', 
        'block_date',
        'therapist'
    ]
    search_fields = ['reason']
    date_hierarchy = 'block_date'
    ordering = ['-block_date', 'start_time']
    list_editable = ['is_active']  # 実際のフィールドなので編集可能
    
    fieldsets = (
        ('ブロック設定', {
            'fields': ('therapist', 'block_date', 'start_time', 'end_time')
        }),
        ('詳細情報', {
            'fields': ('block_type', 'reason', 'is_active')
        }),
        ('システム情報', {
            'fields': ('is_auto_generated', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'duration_display']
    
    def therapist_display(self, obj):
        return obj.therapist.display_name if obj.therapist else "全体"
    therapist_display.short_description = '対象施術者'
    
    def time_range(self, obj):
        return f'{obj.start_time} - {obj.end_time}'
    time_range.short_description = '時間帯'
    
    def block_type_display(self, obj):
        colors = {
            'before_opening': 'orange',
            'between_bookings': 'blue',
            'after_closing': 'green',
            'manual': 'purple',
        }
        color = colors.get(obj.block_type, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_block_type_display()
        )
    block_type_display.short_description = 'ブロック種別'
    
    def is_auto_generated_display(self, obj):
        if obj.is_auto_generated:
            return format_html('<span style="color: blue;">自動生成</span>')
        else:
            return format_html('<span style="color: green;">手動作成</span>')
    is_auto_generated_display.short_description = '生成方法'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">有効</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">無効</span>')
    is_active_display.short_description = '状態'
    
    def duration_display(self, obj):
        return f'{obj.duration_minutes}分'
    duration_display.short_description = '時間'
    
    actions = [
        'activate_blocks', 
        'deactivate_blocks', 
        'delete_auto_generated_blocks',
        'regenerate_gap_blocks'
    ]
    
    def activate_blocks(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} 件のブロックを有効にしました。')
    activate_blocks.short_description = '選択したブロックを有効にする'
    
    def deactivate_blocks(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} 件のブロックを無効にしました。')
    deactivate_blocks.short_description = '選択したブロックを無効にする'
    
    def delete_auto_generated_blocks(self, request, queryset):
        auto_generated = queryset.filter(is_auto_generated=True)
        count = auto_generated.count()
        auto_generated.delete()
        self.message_user(request, f'{count} 件の自動生成ブロックを削除しました。')
    delete_auto_generated_blocks.short_description = '自動生成されたブロックを削除する'
    
    def regenerate_gap_blocks(self, request, queryset):
        try:
            settings = BookingSettings.get_current_settings()
            if settings.auto_block_gaps:
                settings.refresh_gap_blocks()
                self.message_user(request, 'すべての空白時間ブロックを再生成しました。')
            else:
                self.message_user(request, '空白時間自動ブロック機能が無効になっています。', level=messages.WARNING)
        except Exception as e:
            self.message_user(request, f'ブロック再生成でエラーが発生しました: {str(e)}', level=messages.ERROR)
    regenerate_gap_blocks.short_description = '空白時間ブロックを再生成する'
    
    def get_readonly_fields(self, request, obj=None):
        """自動生成されたブロックは編集を制限"""
        readonly_fields = list(self.readonly_fields)
        if obj and obj.is_auto_generated:
            readonly_fields.extend(['therapist', 'block_date', 'start_time', 'end_time', 'block_type', 'reason'])
        return readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        """自動生成されたブロックは個別削除を制限"""
        if obj and obj.is_auto_generated:
            return False
        return super().has_delete_permission(request, obj)

# 管理サイトのカスタマイズ
admin.site.site_header = 'GRACE SPA 管理システム'
admin.site.site_title = 'GRACE SPA'
admin.site.index_title = 'システム管理'