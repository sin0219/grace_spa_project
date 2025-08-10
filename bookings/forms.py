from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from .models import Booking, Service, Customer, Therapist
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