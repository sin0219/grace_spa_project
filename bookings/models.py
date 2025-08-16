from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import datetime

class Service(models.Model):
    """サービスモデル"""
    name = models.CharField('サービス名', max_length=100)
    description = models.TextField('説明', blank=True)
    duration_minutes = models.PositiveIntegerField('施術時間（分）')
    price = models.PositiveIntegerField('料金')
    is_active = models.BooleanField('有効', default=True)
    sort_order = models.PositiveIntegerField('表示順', default=0)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'サービス'
        verbose_name_plural = 'サービス'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f'{self.name} ({self.duration_minutes}分 ¥{self.price:,})'

class Therapist(models.Model):
    """施術者モデル"""
    name = models.CharField('名前', max_length=50)
    display_name = models.CharField('表示名', max_length=50, help_text='お客様に表示される名前')
    description = models.TextField('紹介文', blank=True)
    image = models.ImageField('写真', upload_to='therapists/', blank=True, null=True)
    is_active = models.BooleanField('有効', default=True)
    sort_order = models.PositiveIntegerField('表示順', default=0)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '施術者'
        verbose_name_plural = '施術者'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.display_name

class Customer(models.Model):
    """顧客モデル"""
    name = models.CharField('名前', max_length=100)
    email = models.EmailField('メールアドレス', unique=True)
    phone = models.CharField('電話番号', max_length=20)
    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '顧客'
        verbose_name_plural = '顧客'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.email})'
    
    @property
    def booking_count(self):
        """予約回数"""
        return self.booking_set.count()

class Booking(models.Model):
    """予約モデル"""
    STATUS_CHOICES = [
        ('pending', '承認待ち'),
        ('confirmed', '確定'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='顧客')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='サービス')
    therapist = models.ForeignKey(Therapist, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='施術者')
    booking_date = models.DateField('予約日')
    booking_time = models.TimeField('予約時間')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '予約'
        verbose_name_plural = '予約'
        ordering = ['-booking_date', '-booking_time']
        unique_together = ['therapist', 'booking_date', 'booking_time']
    
    def __str__(self):
        therapist_name = self.therapist.display_name if self.therapist else "指名なし"
        return f'{self.customer.name} - {self.service.name} ({self.booking_date} {self.booking_time} / {therapist_name})'
    
    @property
    def end_time(self):
        """施術終了時間"""
        start_datetime = datetime.datetime.combine(self.booking_date, self.booking_time)
        end_datetime = start_datetime + datetime.timedelta(minutes=self.service.duration_minutes)
        return end_datetime.time()

class BusinessHours(models.Model):
    """営業時間モデル"""
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
    last_booking_time = models.TimeField('最終予約受付時間', default='19:00')
    
    class Meta:
        verbose_name = '営業時間'
        verbose_name_plural = '営業時間'
        ordering = ['weekday']
    
    def __str__(self):
        weekday_name = dict(self.WEEKDAY_CHOICES)[self.weekday]
        if self.is_open:
            return f'{weekday_name}: {self.open_time}-{self.close_time}'
        else:
            return f'{weekday_name}: 定休日'

class BookingSettings(models.Model):
    """予約設定モデル"""
    # 基本設定
    booking_interval_minutes = models.PositiveIntegerField(
        '予約間隔（分）',
        default=10,
        validators=[MinValueValidator(5), MaxValueValidator(60)],
        help_text='予約時間の間隔を分単位で設定（5-60分）'
    )
    treatment_buffer_minutes = models.PositiveIntegerField(
        '施術間インターバル（分）',
        default=15,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        help_text='施術と施術の間の休憩時間（0-60分）'
    )
    advance_booking_days = models.PositiveIntegerField(
        '予約受付期間（日）',
        default=90,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='何日先まで予約を受け付けるか（1-365日）'
    )
    same_day_booking_cutoff = models.TimeField(
        '当日予約締切時間',
        default='12:00',
        help_text='この時間以降は当日予約を受け付けない'
    )
    # ②直前予約制限の設定を追加
    min_advance_minutes = models.PositiveIntegerField(
        '直前予約制限時間（分）',
        default=20,
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text='予約は何分前まで受け付けるか（5-120分）※当日のみ適用'
    )
    default_treatment_duration = models.PositiveIntegerField(
        'デフォルト施術時間（分）',
        default=90,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        help_text='新規サービス作成時のデフォルト時間（30-300分）'
    )
    allow_same_time_bookings = models.BooleanField(
        '同時刻予約許可',
        default=False,
        help_text='複数の施術者が同じ時間に予約を取れるかどうか'
    )
    enable_therapist_selection = models.BooleanField(
        '施術者指名機能',
        default=True,
        help_text='お客様が施術者を指名できるかどうか（OFFにすると指名なしの選択肢が非表示になります）'
    )
    
    # 空白時間自動ブロック機能（新規追加）
    auto_block_gaps = models.BooleanField(
        '空白時間の自動ブロック',
        default=True,
        help_text='短い空白時間を自動的に予約不可にする機能を有効にする'
    )
    minimum_gap_minutes = models.PositiveIntegerField(
        '最小空白時間（分）',
        default=90,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        help_text='この時間以下の空白は自動的に予約不可になります（30-300分）'
    )
    gap_block_before_opening = models.BooleanField(
        '営業開始前の空白もブロック',
        default=True,
        help_text='営業開始から最初の予約までの空白時間もブロック対象にする'
    )
    gap_block_after_closing = models.BooleanField(
        '営業終了後の空白もブロック',
        default=True,
        help_text='最後の予約から営業終了までの空白時間もブロック対象にする'
    )
    gap_block_between_bookings = models.BooleanField(
        '予約間の空白をブロック',
        default=True,
        help_text='予約と予約の間の空白時間をブロック対象にする'
    )
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '予約設定'
        verbose_name_plural = '予約設定'
    
    def __str__(self):
        return f'予約設定 (間隔: {self.booking_interval_minutes}分, インターバル: {self.treatment_buffer_minutes}分, 直前制限: {self.min_advance_minutes}分)'
    
    @classmethod
    def get_current_settings(cls):
        """現在の予約設定を取得"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def save(self, *args, **kwargs):
        """保存時の処理"""
        # IDを1に固定（シングルトンパターン）
        self.id = 1
        super().save(*args, **kwargs)
        
        # 設定変更時に自動ブロックを再計算
        if self.auto_block_gaps:
            self.refresh_gap_blocks()
    
    def refresh_gap_blocks(self):
        """空白時間ブロックを再計算・更新"""
        from datetime import datetime, timedelta
        
        # 既存の自動生成されたギャップブロックを削除
        GapBlock.objects.filter(is_auto_generated=True).delete()
        
        # 今日から advance_booking_days 日先まで処理
        today = timezone.now().date()
        end_date = today + timedelta(days=self.advance_booking_days)
        
        current_date = today
        while current_date <= end_date:
            self._generate_gap_blocks_for_date(current_date)
            current_date += timedelta(days=1)
    
    def _generate_gap_blocks_for_date(self, date):
        """指定日のギャップブロックを生成"""
        from datetime import datetime, timedelta
        
        # 営業時間を取得
        weekday = date.weekday()
        try:
            business_hour = BusinessHours.objects.get(weekday=weekday)
            if not business_hour.is_open:
                return  # 休業日はスキップ
        except BusinessHours.DoesNotExist:
            return
        
        # その日の確定済み予約を取得（施術者別に処理）
        therapists = list(Therapist.objects.filter(is_active=True)) + [None]  # 指名なしも含む
        
        for therapist in therapists:
            self._generate_gap_blocks_for_therapist_date(date, therapist, business_hour)
    
    def _generate_gap_blocks_for_therapist_date(self, date, therapist, business_hour):
        """指定日・施術者のギャップブロックを生成"""
        from datetime import datetime, timedelta
        
        # その施術者のその日の予約を取得
        bookings = Booking.objects.filter(
            booking_date=date,
            status__in=['confirmed', 'pending'],
            therapist=therapist
        ).order_by('booking_time')
        
        if not bookings.exists():
            return  # 予約がない日はスキップ
        
        gap_blocks_to_create = []
        
        # 1. 営業開始から最初の予約までの空白
        if self.gap_block_before_opening:
            first_booking = bookings.first()
            gap_minutes = self._calculate_time_gap(
                business_hour.open_time,
                first_booking.booking_time
            )
            
            if 0 < gap_minutes <= self.minimum_gap_minutes:
                gap_blocks_to_create.append({
                    'therapist': therapist,
                    'date': date,
                    'start_time': business_hour.open_time,
                    'end_time': first_booking.booking_time,
                    'block_type': 'before_opening',
                    'reason': f'営業開始前の空白時間（{gap_minutes}分）'
                })
        
        # 2. 予約間の空白
        if self.gap_block_between_bookings:
            for i in range(len(bookings) - 1):
                current_booking = bookings[i]
                next_booking = bookings[i + 1]
                
                # 現在の予約終了時間 + バッファ
                current_end_time = self._add_minutes_to_time(
                    current_booking.booking_time,
                    current_booking.service.duration_minutes + self.treatment_buffer_minutes
                )
                
                gap_minutes = self._calculate_time_gap(current_end_time, next_booking.booking_time)
                
                if 0 < gap_minutes <= self.minimum_gap_minutes:
                    gap_blocks_to_create.append({
                        'therapist': therapist,
                        'date': date,
                        'start_time': current_end_time,
                        'end_time': next_booking.booking_time,
                        'block_type': 'between_bookings',
                        'reason': f'予約間の空白時間（{gap_minutes}分）'
                    })
        
        # 3. 最後の予約から営業終了までの空白
        if self.gap_block_after_closing:
            last_booking = bookings.last()
            last_end_time = self._add_minutes_to_time(
                last_booking.booking_time,
                last_booking.service.duration_minutes + self.treatment_buffer_minutes
            )
            
            gap_minutes = self._calculate_time_gap(last_end_time, business_hour.last_booking_time)
            
            if 0 < gap_minutes <= self.minimum_gap_minutes:
                gap_blocks_to_create.append({
                    'therapist': therapist,
                    'date': date,
                    'start_time': last_end_time,
                    'end_time': business_hour.last_booking_time,
                    'block_type': 'after_closing',
                    'reason': f'営業終了前の空白時間（{gap_minutes}分）'
                })
        
        # ギャップブロックを一括作成
        for gap_data in gap_blocks_to_create:
            GapBlock.objects.create(
                therapist=gap_data['therapist'],
                block_date=gap_data['date'],
                start_time=gap_data['start_time'],
                end_time=gap_data['end_time'],
                block_type=gap_data['block_type'],
                reason=gap_data['reason'],
                is_auto_generated=True,
                is_active=True
            )
    
    def _calculate_time_gap(self, start_time, end_time):
        """2つの時間の間隔を分単位で計算"""
        from datetime import datetime, timedelta
        
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        return end_minutes - start_minutes
    
    def _add_minutes_to_time(self, time_obj, minutes):
        """時刻に分数を加算"""
        from datetime import datetime, timedelta
        
        dt = datetime.combine(datetime.today(), time_obj)
        dt += timedelta(minutes=minutes)
        return dt.time()

class Schedule(models.Model):
    """予定モデル（休憩、会議、研修等）"""
    SCHEDULE_TYPE_CHOICES = [
        ('break', '休憩'),
        ('meeting', '会議・打ち合わせ'),
        ('training', '研修・勉強'),
        ('maintenance', 'メンテナンス'),
        ('preparation', '準備・片付け'),
        ('admin', '事務作業'),
        ('other', 'その他'),
    ]
    
    title = models.CharField('タイトル', max_length=100)
    schedule_type = models.CharField('予定種別', max_length=20, choices=SCHEDULE_TYPE_CHOICES)
    therapist = models.ForeignKey(
        Therapist, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name='担当者',
        help_text='特定の施術者に関連する予定の場合のみ選択'
    )
    schedule_date = models.DateField('予定日')
    start_time = models.TimeField('開始時間')
    end_time = models.TimeField('終了時間')
    description = models.TextField('詳細・備考', blank=True)
    is_recurring = models.BooleanField('繰り返し予定', default=False)
    is_active = models.BooleanField('有効', default=True)
    created_by = models.CharField('作成者', max_length=100, default='system')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '予定'
        verbose_name_plural = '予定'
        ordering = ['-schedule_date', 'start_time']
    
    def __str__(self):
        therapist_name = self.therapist.display_name if self.therapist else "全体"
        return f'{self.title} ({self.schedule_date} {self.start_time}-{self.end_time} / {therapist_name})'
    
    @property
    def duration_minutes(self):
        """予定の時間（分）"""
        start_datetime = datetime.datetime.combine(self.schedule_date, self.start_time)
        end_datetime = datetime.datetime.combine(self.schedule_date, self.end_time)
        duration = end_datetime - start_datetime
        return int(duration.total_seconds() / 60)
    
    def conflicts_with_bookings(self):
        """この予定と重複する予約を取得"""
        conflicting_bookings = Booking.objects.filter(
            booking_date=self.schedule_date,
            status__in=['pending', 'confirmed']
        )
        
        if self.therapist:
            conflicting_bookings = conflicting_bookings.filter(therapist=self.therapist)
        
        # 時間の重複をチェック
        conflicts = []
        for booking in conflicting_bookings:
            booking_start = datetime.datetime.combine(self.schedule_date, booking.booking_time)
            booking_end = booking_start + datetime.timedelta(minutes=booking.service.duration_minutes)
            
            schedule_start = datetime.datetime.combine(self.schedule_date, self.start_time)
            schedule_end = datetime.datetime.combine(self.schedule_date, self.end_time)
            
            # 重複チェック
            if (schedule_start < booking_end and schedule_end > booking_start):
                conflicts.append(booking)
        
        return conflicts

class GapBlock(models.Model):
    """空白時間ブロックモデル（新規追加）"""
    BLOCK_TYPE_CHOICES = [
        ('before_opening', '営業開始前'),
        ('between_bookings', '予約間'),
        ('after_closing', '営業終了前'),
        ('manual', '手動設定'),
    ]
    
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='対象施術者',
        help_text='特定の施術者のブロック（空白の場合は全体）'
    )
    block_date = models.DateField('ブロック日')
    start_time = models.TimeField('開始時間')
    end_time = models.TimeField('終了時間')
    block_type = models.CharField('ブロック種別', max_length=20, choices=BLOCK_TYPE_CHOICES)
    reason = models.CharField('理由', max_length=200)
    is_auto_generated = models.BooleanField('自動生成', default=True)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '空白時間ブロック'
        verbose_name_plural = '空白時間ブロック'
        ordering = ['-block_date', 'start_time']
        indexes = [
            models.Index(fields=['block_date', 'therapist']),
            models.Index(fields=['is_active', 'is_auto_generated']),
        ]
    
    def __str__(self):
        therapist_name = self.therapist.display_name if self.therapist else "全体"
        return f'{self.get_block_type_display()}: {self.block_date} {self.start_time}-{self.end_time} ({therapist_name})'
    
    @property
    def duration_minutes(self):
        """ブロック時間（分）"""
        start_datetime = datetime.datetime.combine(self.block_date, self.start_time)
        end_datetime = datetime.datetime.combine(self.block_date, self.end_time)
        duration = end_datetime - start_datetime
        return int(duration.total_seconds() / 60)
    
    def save(self, *args, **kwargs):
        """保存時の検証"""
        if self.start_time >= self.end_time:
            raise ValidationError('開始時間は終了時間より前に設定してください。')
        super().save(*args, **kwargs)
    
    @classmethod
    def get_blocks_for_date_therapist(cls, date, therapist=None):
        """指定日・施術者の有効なブロックを取得"""
        blocks = cls.objects.filter(
            block_date=date,
            is_active=True
        )
        
        if therapist:
            # 指定施術者のブロック + 全体ブロック
            blocks = blocks.filter(
                models.Q(therapist=therapist) | models.Q(therapist__isnull=True)
            )
        else:
            # 全体ブロックのみ
            blocks = blocks.filter(therapist__isnull=True)
        
        return blocks.order_by('start_time')