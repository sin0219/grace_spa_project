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
        queryset=Service.objects.filter(is_active=True),
        label='ご希望のサービスをお選びください',
        widget=forms.RadioSelect(attrs={'class': 'service-radio'}),
        empty_label=None
    )

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
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        therapist = cleaned_data.get('therapist')
        
        if booking_date and booking_time:
            # セッションからサービス情報を取得（リクエストオブジェクトが必要なため、ビューで処理）
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
    
    def clean_customer_email(self):
        email = self.cleaned_data['customer_email']
        
        # 本日の同一メールアドレスでの予約数をチェック
        today = timezone.now().date()
        daily_bookings = Booking.objects.filter(
            customer__email=email,
            created_at__date=today
        ).count()
        
        daily_limit = getattr(settings, 'BOOKING_DAILY_LIMIT_PER_EMAIL', 2)
        
        if daily_bookings >= daily_limit:
            raise ValidationError(
                f'申し訳ございません。同一メールアドレスでの1日の予約は{daily_limit}件までとさせていただいております。'
            )
        
        return email
    
    def clean_customer_phone(self):
        phone = self.cleaned_data['customer_phone']
        
        # 本日の同一電話番号での予約数をチェック
        today = timezone.now().date()
        daily_bookings = Booking.objects.filter(
            customer__phone=phone,
            created_at__date=today
        ).count()
        
        daily_limit = getattr(settings, 'BOOKING_DAILY_LIMIT_PER_PHONE', 2)
        
        if daily_bookings >= daily_limit:
            raise ValidationError(
                f'申し訳ございません。同一電話番号での1日の予約は{daily_limit}件までとさせていただいております。'
            )
        
        return phone

def validate_booking_time_slot(service, booking_date, booking_time, therapist=None):
    """
    予約時間の妥当性をチェックする関数（予定も含む）
    サービス時間 + インターバル時間を考慮して重複チェック
    """
    try:
        booking_settings = BookingSettings.get_current_settings()
        buffer_minutes = booking_settings.treatment_buffer_minutes
        interval_minutes = booking_settings.booking_interval_minutes
    except:
        buffer_minutes = 15   # デフォルト15分インターバル
        interval_minutes = 10  # デフォルト10分刻み
    
    # 指定日の既存予約を取得
    existing_bookings = Booking.objects.filter(
        booking_date=booking_date,
        status__in=['pending', 'confirmed']
    )
    
    # 施術者が指定されている場合は、その施術者の予約をチェック
    if therapist:
        existing_bookings = existing_bookings.filter(therapist=therapist)
    else:
        # 施術者指定なしの場合は、指定なしの予約のみチェック
        existing_bookings = existing_bookings.filter(therapist__isnull=True)
    
    # 指定日の既存予定を取得（新規追加）
    try:
        existing_schedules = Schedule.objects.filter(
            schedule_date=booking_date,
            is_active=True
        )
        
        # 施術者が指定されている場合は、その施術者の予定または全体予定をチェック
        if therapist:
            existing_schedules = existing_schedules.filter(
                Q(therapist=therapist) | Q(therapist__isnull=True)
            )
        # 施術者指定なしの場合は、全体予定のみチェック
        else:
            existing_schedules = existing_schedules.filter(therapist__isnull=True)
    except:
        existing_schedules = []
    
    # 新しい予約の時間帯を計算
    new_booking_start = datetime.datetime.combine(booking_date, booking_time)
    new_booking_end = new_booking_start + datetime.timedelta(minutes=service.duration_minutes + buffer_minutes)
    
    # 既存予約との重複チェック
    for existing_booking in existing_bookings:
        existing_start = datetime.datetime.combine(booking_date, existing_booking.booking_time)
        existing_end = existing_start + datetime.timedelta(
            minutes=existing_booking.service.duration_minutes + buffer_minutes
        )
        
        # 時間帯が重複するかチェック
        if (new_booking_start < existing_end and new_booking_end > existing_start):
            therapist_name = therapist.display_name if therapist else "指名なし"
            raise ValidationError(
                f'申し訳ございません。{therapist_name}の{booking_time}は既に予約が入っているか、'
                f'前後の施術時間と重複しています。別の時間をお選びください。'
            )
    
    # 既存予定との重複チェック（新規追加）
    for existing_schedule in existing_schedules:
        schedule_start = datetime.datetime.combine(booking_date, existing_schedule.start_time)
        schedule_end = datetime.datetime.combine(booking_date, existing_schedule.end_time)
        
        # 予約時間が予定時間と重複するかチェック
        if (new_booking_start < schedule_end and new_booking_end > schedule_start):
            therapist_name = therapist.display_name if therapist else "指名なし"
            schedule_info = f"{existing_schedule.title}（{existing_schedule.get_schedule_type_display()}）"
            raise ValidationError(
                f'申し訳ございません。{therapist_name}の{booking_time}は予定「{schedule_info}」と'
                f'重複しています。別の時間をお選びください。'
            )
    
    return True