from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

class BusinessHours(models.Model):
    """営業時間・基本設定"""
    WEEKDAY_CHOICES = [
        (0, '月曜日'),
        (1, '火曜日'),
        (2, '水曜日'),
        (3, '木曜日'),
        (4, '金曜日'),
        (5, '土曜日'),
        (6, '日曜日'),
    ]
    
    weekday = models.IntegerField('曜日', choices=WEEKDAY_CHOICES, unique=True)
    is_open = models.BooleanField('営業日', default=True)
    open_time = models.TimeField('開店時間', default='09:00')
    close_time = models.TimeField('閉店時間', default='20:00')
    last_booking_time = models.TimeField('最終予約受付時間', default='19:00', 
                                       help_text='この時間以降の予約は受け付けません')
    
    class Meta:
        verbose_name = '営業時間'
        verbose_name_plural = '営業時間'
        ordering = ['weekday']
    
    def clean(self):
        if self.is_open:
            if self.open_time >= self.close_time:
                raise ValidationError('開店時間は閉店時間より前に設定してください。')
            if self.last_booking_time > self.close_time:
                raise ValidationError('最終予約受付時間は閉店時間より前に設定してください。')
    
    def __str__(self):
        weekday_name = dict(self.WEEKDAY_CHOICES)[self.weekday]
        if self.is_open:
            return f"{weekday_name}: {self.open_time}-{self.close_time} (最終受付: {self.last_booking_time})"
        else:
            return f"{weekday_name}: 定休日"

class BookingSettings(models.Model):
    """予約システム設定"""
    # 時間間隔設定
    booking_interval_minutes = models.IntegerField('予約時間間隔（分）', default=30,
                                                  help_text='予約可能な時間の間隔（例：30分ごと）')
    treatment_buffer_minutes = models.IntegerField('施術間インターバル（分）', default=15,
                                                  help_text='施術と施術の間の準備時間')
    
    # 予約制限設定
    advance_booking_days = models.IntegerField('事前予約可能日数', default=90,
                                             help_text='何日先まで予約を受け付けるか')
    same_day_booking_cutoff = models.TimeField('当日予約締切時間', default='12:00',
                                             help_text='当日予約の受付締切時間')
    
    # 施術時間設定
    default_treatment_duration = models.IntegerField('標準施術時間（分）', default=90,
                                                   help_text='何も指定がない場合の施術時間')
    
    # その他設定
    allow_same_time_bookings = models.BooleanField('同時刻複数予約許可', default=False,
                                                 help_text='複数の施術者がいる場合、同じ時刻の予約を許可するか')
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '予約設定'
        verbose_name_plural = '予約設定'
    
    def __str__(self):
        return f"予約設定 (更新: {self.updated_at.strftime('%Y/%m/%d %H:%M')})"
    
    @classmethod
    def get_current_settings(cls):
        """現在の設定を取得（なければデフォルト作成）"""
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'booking_interval_minutes': 30,
                'treatment_buffer_minutes': 15,
                'advance_booking_days': 90,
                'same_day_booking_cutoff': '12:00',
                'default_treatment_duration': 90,
                'allow_same_time_bookings': False,
            }
        )
        return settings

class Therapist(models.Model):
    """施術者"""
    name = models.CharField('お名前', max_length=100)
    display_name = models.CharField('表示名', max_length=100, help_text='お客様に表示される名前')
    # photo = models.ImageField('写真', upload_to='therapists/', blank=True, null=True)  # 一時的にコメントアウト
    introduction = models.TextField('自己紹介', blank=True, help_text='経歴や得意な施術など')
    specialties = models.TextField('得意な施術', blank=True, help_text='専門分野や得意なマッサージ技術')
    experience_years = models.IntegerField('経験年数', default=0)
    is_active = models.BooleanField('有効', default=True, help_text='予約受付中かどうか')
    is_featured = models.BooleanField('おすすめ', default=False, help_text='トップページで強調表示')
    sort_order = models.IntegerField('表示順', default=0, help_text='小さい数字ほど上に表示')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '施術者'
        verbose_name_plural = '施術者'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    @property
    def total_bookings(self):
        """総予約数"""
        return self.booking_set.filter(status='completed').count()
    
    @property
    def this_month_bookings(self):
        """今月の予約数"""
        now = timezone.now()
        return self.booking_set.filter(
            status='completed',
            booking_date__year=now.year,
            booking_date__month=now.month
        ).count()

class Service(models.Model):
    """サービス・メニュー"""
    name = models.CharField('サービス名', max_length=100)
    duration_minutes = models.IntegerField('時間（分）')
    price = models.IntegerField('料金')
    description = models.TextField('説明', blank=True)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = 'サービス'
        verbose_name_plural = 'サービス'
    
    def __str__(self):
        return f"{self.name} ({self.duration_minutes}分) - ¥{self.price:,}"

class Customer(models.Model):
    """顧客情報"""
    name = models.CharField('お名前', max_length=100)
    email = models.EmailField('メールアドレス')
    phone_regex = RegexValidator(
        regex=r'^[0-9\-]+$', 
        message="電話番号は数字とハイフンのみ入力可能です。"
    )
    phone = models.CharField('電話番号', validators=[phone_regex], max_length=20)
    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '顧客'
        verbose_name_plural = '顧客'
    
    def __str__(self):
        return f"{self.name} ({self.email})"

class Booking(models.Model):
    """予約情報"""
    STATUS_CHOICES = [
        ('pending', '予約申込中'),
        ('confirmed', '予約確定'),
        ('completed', '施術完了'),
        ('cancelled', 'キャンセル'),
        ('no_show', '無断キャンセル'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='顧客')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='サービス')
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, verbose_name='施術者', blank=True, null=True)
    booking_date = models.DateField('予約日')
    booking_time = models.TimeField('予約時間')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '予約'
        verbose_name_plural = '予約'
        unique_together = ['booking_date', 'booking_time', 'therapist']
    
    def __str__(self):
        therapist_name = f" - {self.therapist.display_name}" if self.therapist else ""
        return f"{self.customer.name} - {self.service.name}{therapist_name} ({self.booking_date} {self.booking_time})"
    
    @property
    def is_past(self):
        """過去の予約かどうか"""
        booking_datetime = timezone.make_aware(
            timezone.datetime.combine(self.booking_date, self.booking_time)
        )
        return booking_datetime < timezone.now()