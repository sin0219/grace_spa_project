from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from .models import EmailTemplate, EmailLog, MailSettings
from .utils import send_test_email


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type_display', 'subject_short', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject', 'body_text']
    ordering = ['template_type', 'name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'template_type', 'is_active')
        }),
        ('メール内容', {
            'fields': ('subject', 'body_text', 'body_html')
        }),
    )
    
    def template_type_display(self, obj):
        return obj.get_template_type_display()
    template_type_display.short_description = 'テンプレート種別'
    
    def subject_short(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_short.short_description = '件名'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 編集時
            return ['template_type']
        return []
    
    class Media:
        css = {
            'all': ('admin/css/email_template.css',)
        }


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject_short', 'status_display', 'template_link', 'booking_link', 'sent_at', 'retry_count']
    list_filter = ['status', 'template__template_type', 'sent_at', 'created_at']
    search_fields = ['recipient_email', 'recipient_name', 'subject', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('送信情報', {
            'fields': ('recipient_email', 'recipient_name', 'status', 'sent_at', 'retry_count')
        }),
        ('メール内容', {
            'fields': ('template', 'subject', 'body_text', 'body_html')
        }),
        ('関連情報', {
            'fields': ('booking', 'scheduled_at', 'error_message')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    actions = ['retry_failed_emails', 'mark_as_sent']
    
    def subject_short(self, obj):
        return obj.subject[:40] + '...' if len(obj.subject) > 40 else obj.subject
    subject_short.short_description = '件名'
    
    def status_display(self, obj):
        status_colors = {
            'pending': '#ffc107',
            'sent': '#28a745',
            'failed': '#dc3545',
            'retry': '#fd7e14',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '送信状況'
    
    def template_link(self, obj):
        if obj.template:
            url = reverse('admin:emails_emailtemplate_change', args=[obj.template.pk])
            return format_html('<a href="{}">{}</a>', url, obj.template.name)
        return '-'
    template_link.short_description = 'テンプレート'
    
    def booking_link(self, obj):
        if obj.booking:
            url = reverse('admin:bookings_booking_change', args=[obj.booking.pk])
            return format_html('<a href="{}">{}</a>', url, str(obj.booking))
        return '-'
    booking_link.short_description = '関連予約'
    
    def retry_failed_emails(self, request, queryset):
        failed_emails = queryset.filter(status='failed')
        count = 0
        for email_log in failed_emails:
            email_log.status = 'retry'
            email_log.retry_count += 1
            email_log.save()
            count += 1
        
        self.message_user(
            request,
            f'{count}件のメールを再送信待ちに変更しました。',
            messages.SUCCESS
        )
    retry_failed_emails.short_description = '失敗したメールを再送信待ちにする'
    
    def mark_as_sent(self, request, queryset):
        pending_emails = queryset.filter(status='pending')
        count = 0
        for email_log in pending_emails:
            email_log.status = 'sent'
            email_log.sent_at = timezone.now()
            email_log.save()
            count += 1
        
        self.message_user(
            request,
            f'{count}件のメールを送信済みに変更しました。',
            messages.SUCCESS
        )
    mark_as_sent.short_description = '送信済みとしてマークする'


@admin.register(MailSettings)
class MailSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('基本設定', {
            'fields': ('from_email', 'from_name', 'reply_to_email')
        }),
        ('管理者設定', {
            'fields': ('admin_email', 'admin_name')
        }),
        ('通知設定', {
            'fields': ('enable_customer_notifications', 'enable_admin_notifications', 'enable_reminder_emails')
        }),
        ('リマインダー設定', {
            'fields': ('reminder_hours_before',)
        }),
        ('メール署名', {
            'fields': ('signature',)
        }),
    )
    
    def has_add_permission(self, request):
        # 既に設定が存在する場合は追加を許可しない
        return not MailSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 削除を許可しない
        return False
    
    def changelist_view(self, request, extra_context=None):
        # 設定が存在しない場合は作成画面へリダイレクト
        if not MailSettings.objects.exists():
            return HttpResponseRedirect(reverse('admin:emails_mailsettings_add'))
        
        # 設定が存在する場合は編集画面へリダイレクト
        settings_obj = MailSettings.objects.first()
        return HttpResponseRedirect(reverse('admin:emails_mailsettings_change', args=[settings_obj.pk]))
    
    def response_change(self, request, obj):
        if '_test_email' in request.POST:
            # テストメール送信
            try:
                result = send_test_email(obj.admin_email)
                if result:
                    self.message_user(
                        request,
                        f'テストメールを {obj.admin_email} に送信しました。',
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request,
                        'テストメールの送信に失敗しました。設定を確認してください。',
                        messages.ERROR
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f'テストメール送信エラー: {str(e)}',
                    messages.ERROR
                )
            return HttpResponseRedirect(request.get_full_path())
        
        return super().response_change(request, obj)
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新規作成時
            obj.pk = 1  # PKを固定
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/mail_settings.css',)
        }
        js = ('admin/js/mail_settings.js',)