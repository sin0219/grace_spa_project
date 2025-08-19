from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from .models import Booking, Service, Customer, Therapist, BookingSettings, Schedule
import datetime

# ===== 3ステップ予約フォーム =====

class ServiceSelectionForm(forms.Form):
    """ステップ1: サービス選択フォーム"""
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='ご希望のサービスをお選びください',
        widget=forms.RadioSelect(attrs={'class': 'service-radio'}),
        empty_label=None,
        to_field_name='id'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # アクティブなサービスのみを表示
        self.fields['service'].queryset = Service.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    def clean_service(self):
        service = self.cleaned_data['service']
        if not service.is_active:
            raise ValidationError('選択されたサービスは現在ご利用いただけません。')
        return service

class DateTimeTherapistForm(forms.Form):
    """ステップ2: 日時・施術者選択フォーム"""
    therapist = forms.ModelChoiceField(
        queryset=Therapist.objects.filter(is_active=True),
        label='施術者',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'therapist-radio'}),
        empty_label='指名なし（どなたでも）'
    )
    booking_date = forms.DateField(
        label='ご希望日',
        widget=forms.HiddenInput()
    )
    booking_time = forms.TimeField(
        label='ご希望時間',
        widget=forms.HiddenInput()
    )
    notes = forms.CharField(
        label='ご要望・備考',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ご質問やご要望があればお書きください'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.enable_therapist_selection = kwargs.pop('enable_therapist_selection', True)
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        if not self.enable_therapist_selection:
            self.fields['therapist'].widget = forms.HiddenInput()
            self.fields['therapist'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        therapist = cleaned_data.get('therapist')
        
        if booking_date and booking_time and self.service:
            # 時間重複チェック（フォームレベルではバリデーションのみ、実際のチェックはビューで処理）
            try:
                validate_booking_time_slot(self.service, booking_date, booking_time, therapist)
            except ValidationError:
                # フォームレベルでは詳細なエラーメッセージを表示せず、ビューで処理させる
                pass
        
        return cleaned_data

class CustomerInfoForm(forms.Form):
    """ステップ3: お客様情報入力フォーム"""
    customer_name = forms.CharField(
        label='お名前',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '山田太郎'
        })
    )
    customer_email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@example.com'
        })
    )
    customer_phone = forms.CharField(
        label='電話番号',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '090-1234-5678'
        })
    )
    
    # 新しく追加するフィールド
    GENDER_CHOICES = [
        ('male', '男性'),
        ('female', '女性'),
    ]
    
    gender = forms.ChoiceField(
        label='性別',
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    is_first_visit = forms.BooleanField(
        label='当店の利用は初めてですか？',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    terms_confirmed = forms.BooleanField(
        label='確認しました',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
   
    
    def clean_customer_email(self):
        email = self.cleaned_data['customer_email']
        
        # 本日の同一メールアドレスでの予約数をチェック
        today = timezone.now().date()
        daily_bookings = Booking.objects.filter(
            customer__email=email,
            created_at__date=today
        ).count()
        
        daily_limit = getattr(settings, 'BOOKING_DAILY_LIMIT_PER_EMAIL', 3)
        
        if daily_bookings >= daily_limit:
            raise ValidationError(
                f'申し訳ございませんが、同一メールアドレスでの1日の予約は{daily_limit}件までとなっております。'
            )
        
        return email

# ===== バリデーション関数 =====

def validate_booking_time_slot(service, booking_date, booking_time, therapist=None):
    """
    予約時間の重複チェック（①当日時刻チェック ②直前予約制限対応）
    """
    from django.db import models
    
    # 現在時刻を取得（aware datetime）
    now = timezone.now()
    current_date = now.date()
    
    # 予約設定を取得
    try:
        booking_settings = BookingSettings.get_current_settings()
        # ②直前予約制限の設定を取得
        min_advance_minutes = getattr(booking_settings, 'min_advance_minutes', 20)  # デフォルト20分
    except BookingSettings.DoesNotExist:
        min_advance_minutes = 20  # デフォルト20分前まで
    
    # ①当日予約の場合の時刻チェック
    if booking_date == current_date:
        # 予約日時をaware datetimeに変換
        booking_datetime = timezone.make_aware(
            datetime.datetime.combine(booking_date, booking_time)
        )
        
        # 現在時刻より前の時間は予約不可
        if booking_datetime <= now:
            raise ValidationError('過去の時間は予約できません。')
        
        # ②直前予約制限チェック
        min_booking_datetime = now + datetime.timedelta(minutes=min_advance_minutes)
        
        if booking_datetime < min_booking_datetime:
            raise ValidationError(
                f'申し訳ございませんが、予約は{min_advance_minutes}分前までにお取りください。'
            )
    
    # 予約開始時刻と終了時刻を計算（naive datetimeのまま処理）
    booking_datetime_naive = datetime.datetime.combine(booking_date, booking_time)
    end_datetime_naive = booking_datetime_naive + datetime.timedelta(minutes=service.duration_minutes)
    
    # 既存の予約をチェック
    overlapping_bookings = Booking.objects.filter(
        booking_date=booking_date,
        status__in=['pending', 'confirmed']  # キャンセル済みは除外
    )
    
    # 施術者が指定されている場合は同じ施術者の予約のみチェック
    if therapist:
        overlapping_bookings = overlapping_bookings.filter(therapist=therapist)
    
    # 時間の重複をチェック
    for booking in overlapping_bookings:
        existing_start = datetime.datetime.combine(booking.booking_date, booking.booking_time)
        existing_end = existing_start + datetime.timedelta(minutes=booking.service.duration_minutes)
        
        # 時間の重複判定
        if (booking_datetime_naive < existing_end and end_datetime_naive > existing_start):
            if therapist:
                raise ValidationError(f'選択された時間は{therapist.display_name}の予約が重複しています。別の時間をお選びください。')
            else:
                raise ValidationError('選択された時間は既に予約が入っています。別の時間をお選びください。')
    
    # 予約設定による制限チェック
    try:
        booking_settings = BookingSettings.get_current_settings()
        
        # 予約可能な最大日数をチェック（正しいフィールド名に修正）
        max_days_ahead = booking_settings.advance_booking_days
        if max_days_ahead > 0:
            max_date = timezone.now().date() + datetime.timedelta(days=max_days_ahead)
            if booking_date > max_date:
                raise ValidationError(f'予約は{max_days_ahead}日先まで可能です。')
        
        # 当日予約の制限チェック（従来の制限と併用）
        if booking_date == timezone.now().date():
            cutoff_time = booking_settings.same_day_booking_cutoff
            current_time = timezone.now().time()
            if current_time > cutoff_time:
                raise ValidationError(f'当日の予約は{cutoff_time.strftime("%H:%M")}まで受け付けています。')
                
    except BookingSettings.DoesNotExist:
        pass
    
    # 営業時間チェック
    from .models import BusinessHours
    try:
        business_hours = BusinessHours.objects.filter(
            weekday=booking_date.weekday(),
            is_open=True
        ).first()
        
        if not business_hours:
            raise ValidationError('選択された日は休業日です。')
        
        if booking_time < business_hours.open_time or end_datetime_naive.time() > business_hours.close_time:
            raise ValidationError('選択された時間は営業時間外です。')
            
    except BusinessHours.DoesNotExist:
        raise ValidationError('営業時間が設定されていません。')

    # スケジュール（予定）との重複チェック
    from .models import Schedule
    conflicting_schedules = Schedule.objects.filter(
        schedule_date=booking_date,
        is_active=True
    )
    
    # 施術者が指定されている場合は、その施術者の予定のみチェック
    if therapist:
        conflicting_schedules = conflicting_schedules.filter(
            models.Q(therapist=therapist) | models.Q(therapist__isnull=True)  # 全体予定も含む
        )
    
    # 時間の重複チェック
    for schedule in conflicting_schedules:
        schedule_start = datetime.datetime.combine(schedule.schedule_date, schedule.start_time)
        schedule_end = datetime.datetime.combine(schedule.schedule_date, schedule.end_time)
        
        # 時間の重複判定
        if (booking_datetime_naive < schedule_end and end_datetime_naive > schedule_start):
            if therapist and schedule.therapist == therapist:
                raise ValidationError(f'選択された時間は{therapist.display_name}の予定「{schedule.title}」と重複しています。')
            elif schedule.therapist is None:
                raise ValidationError(f'選択された時間は予定「{schedule.title}」と重複しています。')
    
    return True

# ===== その他のフォーム =====

class BookingCancelForm(forms.Form):
    """予約キャンセルフォーム"""
    reason = forms.CharField(
        label='キャンセル理由',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'キャンセル理由をお書きください（任意）'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.booking = kwargs.pop('booking', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.booking:
            # ①当日キャンセルの時刻制限
            now = timezone.now()
            current_date = now.date()
            
            # キャンセル可能期限をチェック
            try:
                booking_settings = BookingSettings.get_current_settings()
                cutoff_time = booking_settings.same_day_booking_cutoff
                # ②直前キャンセル制限の設定を取得
                min_advance_minutes = getattr(booking_settings, 'min_advance_minutes', 20)
                
                # 当日キャンセルの制限例
                if self.booking.booking_date == current_date:
                    # 従来の制限時間チェック
                    current_time = timezone.now().time()
                    if current_time > cutoff_time:
                        raise ValidationError(
                            f'当日の{cutoff_time.strftime("%H:%M")}以降はキャンセルできません。お電話でお問い合わせください。'
                        )
                    
                    # ②直前キャンセル制限チェック
                    booking_datetime = timezone.make_aware(
                        datetime.datetime.combine(self.booking.booking_date, self.booking.booking_time)
                    )
                    min_cancel_datetime = now + datetime.timedelta(minutes=min_advance_minutes)
                    
                    if booking_datetime < min_cancel_datetime:
                        raise ValidationError(
                            f'申し訳ございませんが、予約の{min_advance_minutes}分前以降はキャンセルできません。お電話でお問い合わせください。'
                        )
                        
            except BookingSettings.DoesNotExist:
                # デフォルトの直前キャンセル制限（20分前）
                min_advance_minutes = 20
                if self.booking.booking_date == current_date:
                    booking_datetime = timezone.make_aware(
                        datetime.datetime.combine(self.booking.booking_date, self.booking.booking_time)
                    )
                    min_cancel_datetime = now + datetime.timedelta(minutes=min_advance_minutes)
                    
                    if booking_datetime < min_cancel_datetime:
                        raise ValidationError(
                            f'申し訳ございませんが、予約の{min_advance_minutes}分前以降はキャンセルできません。お電話でお問い合わせください。'
                        )
        
        return cleaned_data