from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class EmailTemplate(models.Model):
    """メールテンプレートモデル"""
    
    TEMPLATE_TYPES = [
        ('booking_confirmation_customer', '顧客向け予約確認'),
        ('booking_confirmation_admin', '管理者向け新規予約通知'),
        ('booking_reminder', '予約リマインダー'),
        ('booking_cancelled_customer', '顧客向けキャンセル通知'),
        ('booking_cancelled_admin', '管理者向けキャンセル通知'),
        ('booking_status_changed', '予約ステータス変更通知'),
    ]
    
    name = models.CharField('テンプレート名', max_length=100)
    template_type = models.CharField('テンプレート種別', max_length=50, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField('件名', max_length=200)
    body_text = models.TextField('本文（テキスト）')
    body_html = models.TextField('本文（HTML）', blank=True)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'
        ordering = ['template_type']
    
    def __str__(self):
        return f'{self.name} ({self.get_template_type_display()})'


class EmailLog(models.Model):
    """メール送信ログ"""
    
    STATUS_CHOICES = [
        ('pending', '送信待ち'),
        ('sent', '送信完了'),
        ('failed', '送信失敗'),
        ('retry', '再送信待ち'),
    ]
    
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='テンプレート')
    recipient_email = models.EmailField('送信先メールアドレス')
    recipient_name = models.CharField('送信先名前', max_length=100, blank=True)
    subject = models.CharField('件名', max_length=200)
    body_text = models.TextField('本文（テキスト）')
    body_html = models.TextField('本文（HTML）', blank=True)
    status = models.CharField('送信状況', max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField('エラーメッセージ', blank=True)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='関連予約')
    scheduled_at = models.DateTimeField('送信予定日時', default=timezone.now)
    sent_at = models.DateTimeField('送信日時', null=True, blank=True)
    retry_count = models.IntegerField('再送信回数', default=0)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'メール送信ログ'
        verbose_name_plural = 'メール送信ログ'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.recipient_email} - {self.subject} ({self.get_status_display()})'


class MailSettings(models.Model):
    """メール設定（単一インスタンス）"""
    
    # 基本設定
    from_email = models.EmailField('送信者メールアドレス', default='noreply@gracespa.com')
    from_name = models.CharField('送信者名', max_length=100, default='GRACE SPA')
    reply_to_email = models.EmailField('返信先メールアドレス', blank=True)
    
    # 管理者通知設定
    admin_email = models.EmailField('管理者メールアドレス')
    admin_name = models.CharField('管理者名', max_length=100, default='管理者')
    
    # 送信設定
    enable_customer_notifications = models.BooleanField('顧客への通知メールを有効にする', default=True)
    enable_admin_notifications = models.BooleanField('管理者への通知メールを有効にする', default=True)
    enable_reminder_emails = models.BooleanField('リマインダーメールを有効にする', default=True)
    
    # リマインダー設定
    reminder_hours_before = models.CharField(
        'リマインダー送信時間（時間前）',
        max_length=50,
        default='24,2',
        help_text='カンマ区切りで複数指定可能（例：24,2 = 24時間前と2時間前）'
    )
    
    # メール署名
    signature = models.TextField('メール署名', default='''
――――――――――――――――――
GRACE SPA
〒000-0000 住所をここに記入
TEL: 000-0000-0000
EMAIL: info@gracespa.com
WEB: https://gracespa.com
――――――――――――――――――
''')
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'メール設定'
        verbose_name_plural = 'メール設定'
    
    def __str__(self):
        return 'メール設定'
    
    def save(self, *args, **kwargs):
        # 単一インスタンスを保証
        if not self.pk and MailSettings.objects.exists():
            raise ValueError('メール設定は1つしか作成できません。')
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """設定を取得（存在しない場合は作成）"""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'admin_email': 'admin@gracespa.com',
            }
        )
        return obj
    
    def get_reminder_hours_list(self):
        """リマインダー時間をリストで取得"""
        try:
            return [int(h.strip()) for h in self.reminder_hours_before.split(',') if h.strip()]
        except:
            return [24, 2]  # デフォルト値