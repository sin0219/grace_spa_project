from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from bookings.models import Booking, Service, Customer, Therapist, Schedule
import datetime

class DashboardBookingForm(forms.ModelForm):
    """ダッシュボード用予約登録フォーム"""
    
    # 顧客情報フィールド
    customer_name = forms.CharField(
        label='お客様名',
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
    
    class Meta:
        model = Booking
        fields = ['service', 'therapist', 'booking_date', 'booking_time', 'status', 'notes']
        labels = {
            'service': 'サービス',
            'therapist': '施術者',
            'booking_date': '予約日',
            'booking_time': '予約時間',
            'status': 'ステータス',
            'notes': '備考'
        }
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control'}),
            'therapist': forms.Select(attrs={'class': 'form-control'}),
            'booking_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'booking_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備考があれば入力してください'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # アクティブなサービスのみを選択肢に表示
        self.fields['service'].queryset = Service.objects.filter(is_active=True)
        
        # アクティブな施術者のみを選択肢に表示
        self.fields['therapist'].queryset = Therapist.objects.filter(is_active=True)
        self.fields['therapist'].required = False
        self.fields['therapist'].empty_label = '指名なし'
        
        # 必須フィールドの設定
        self.fields['notes'].required = False
        
        # ステータスのデフォルト
        self.fields['status'].initial = 'confirmed'
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        therapist = cleaned_data.get('therapist')
        service = cleaned_data.get('service')
        
        # 重複チェック（管理者登録なので既存予約との重複チェックは警告のみ）
        if booking_date and booking_time and service:
            from bookings.forms import validate_booking_time_slot
            try:
                validate_booking_time_slot(service, booking_date, booking_time, therapist)
            except ValidationError as e:
                # 管理者なので警告として表示（ブロックはしない）
                self.add_error(None, f"警告: {str(e)} 管理者権限で強制登録されます。")
        
        return cleaned_data
    
    def save(self, commit=True):
        booking = super().save(commit=False)
        
        # 顧客情報を取得または作成
        customer, created = Customer.objects.get_or_create(
            email=self.cleaned_data['customer_email'],
            defaults={
                'name': self.cleaned_data['customer_name'],
                'phone': self.cleaned_data['customer_phone']
            }
        )
        
        # 既存顧客の場合は情報を更新
        if not created:
            customer.name = self.cleaned_data['customer_name']
            customer.phone = self.cleaned_data['customer_phone']
            customer.save()
        
        booking.customer = customer
        
        if commit:
            booking.save()
        
        return booking

class ScheduleForm(forms.ModelForm):
    """予定登録フォーム"""
    
    class Meta:
        model = Schedule
        fields = ['title', 'schedule_type', 'therapist', 'schedule_date', 'start_time', 'end_time', 'description', 'is_recurring']
        labels = {
            'title': 'タイトル',
            'schedule_type': '予定種別',
            'therapist': '担当者',
            'schedule_date': '予定日',
            'start_time': '開始時間',
            'end_time': '終了時間',
            'description': '詳細・備考',
            'is_recurring': '繰り返し予定'
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：昼休み、研修、メンテナンス'
            }),
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
            'therapist': forms.Select(attrs={'class': 'form-control'}),
            'schedule_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '詳細があれば入力してください'
            }),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # アクティブな施術者のみを選択肢に表示
        self.fields['therapist'].queryset = Therapist.objects.filter(is_active=True)
        self.fields['therapist'].required = False
        self.fields['therapist'].empty_label = '全体（担当者なし）'
        
        # 必須フィールドの設定
        self.fields['description'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        schedule_date = cleaned_data.get('schedule_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # 開始時間と終了時間のチェック
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError('開始時間は終了時間より前に設定してください。')
        
        # 既存予約との重複チェック（警告のみ）
        if schedule_date and start_time and end_time:
            conflicting_bookings = Booking.objects.filter(
                booking_date=schedule_date,
                status__in=['pending', 'confirmed'],
                booking_time__gte=start_time,
                booking_time__lt=end_time
            )
            
            therapist = cleaned_data.get('therapist')
            if therapist:
                conflicting_bookings = conflicting_bookings.filter(therapist=therapist)
            
            if conflicting_bookings.exists():
                booking_list = ', '.join([
                    f"{b.customer.name}({b.booking_time})" 
                    for b in conflicting_bookings
                ])
                self.add_error(None, f"警告: この時間帯に以下の予約があります: {booking_list}")
        
        return cleaned_data