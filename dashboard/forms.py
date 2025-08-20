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
    GENDER_CHOICES = [
        ('', '選択してください'),  # 空の選択肢を追加
        ('male', '男性'),
        ('female', '女性'),
    ]
    
    customer_gender = forms.ChoiceField(
        label='性別（予約時の選択）',
        choices=GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='お客様が予約時に選択した性別です。管理者は後で変更可能です。'
    )
    
    # ★ 新規追加: 初回利用フラグ（管理者用）
    customer_is_first_visit = forms.BooleanField(
        label='初回利用',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='初回利用の場合はチェックしてください。'
    )

    # 日時フィールドを隠しフィールドに変更
    booking_date = forms.DateField(
        label='予約日',
        widget=forms.HiddenInput()
    )
    booking_time = forms.TimeField(
        label='予約時間',
        widget=forms.HiddenInput()
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
        
        # 必須フィールドチェック
        if not booking_date:
            raise ValidationError('予約日を選択してください。')
        if not booking_time:
            raise ValidationError('予約時間を選択してください。')
        
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
        
         # ★ 修正: 顧客情報を取得または作成（性別と初回利用フラグを追加）
        customer_defaults = {
            'name': self.cleaned_data['customer_name'],
            'phone': self.cleaned_data['customer_phone']
        }
        
        # 性別が選択されている場合のみ追加
        if self.cleaned_data.get('customer_gender'):
            customer_defaults['gender'] = self.cleaned_data['customer_gender']
        
        # 初回利用フラグを追加
        customer_defaults['is_first_visit'] = self.cleaned_data['customer_is_first_visit']
        
        customer, created = Customer.objects.get_or_create(
            email=self.cleaned_data['customer_email'],
            defaults=customer_defaults
        )
        
        # ★ 修正: 既存顧客の場合は情報を更新（性別の取り扱いに注意）
        if not created:
            customer.name = self.cleaned_data['customer_name']
            customer.phone = self.cleaned_data['customer_phone']
            
            # 性別については管理者が後で手動設定するため、空の場合のみ更新
            if self.cleaned_data.get('customer_gender') and not customer.gender:
                customer.gender = self.cleaned_data['customer_gender']
            
            # 既存顧客の場合、is_first_visitは通常Falseだが、管理者の判断を優先
            customer.is_first_visit = self.cleaned_data['customer_is_first_visit']
            
            customer.save()
        
        booking.customer = customer
        
        if commit:
            booking.save()
        
        return booking


class ScheduleForm(forms.ModelForm):
    """予定登録フォーム"""
    
    # 日時フィールドを隠しフィールドに変更
    schedule_date = forms.DateField(
        label='予定日',
        widget=forms.HiddenInput()
    )
    start_time = forms.TimeField(
        label='開始時間',
        widget=forms.HiddenInput()
    )
    end_time = forms.TimeField(
        label='終了時間',
        widget=forms.HiddenInput()
    )
    
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
        
        # 必須フィールドチェック
        if not schedule_date:
            raise ValidationError('予定日を選択してください。')
        if not start_time:
            raise ValidationError('開始時間を選択してください。')
        if not end_time:
            raise ValidationError('終了時間を選択してください。')
        
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