from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from .models import Booking, Service, Customer, Therapist
import datetime

class BookingForm(forms.ModelForm):
    # 顧客情報フィールド
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
    
    class Meta:
        model = Booking
        fields = ['service', 'therapist', 'booking_date', 'booking_time', 'notes']
        labels = {
            'service': 'ご希望のサービス',
            'therapist': 'ご希望の施術者',
            'booking_date': 'ご希望日',
            'booking_time': 'ご希望時間',
            'notes': 'ご要望・備考'
        }
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control'}),
            'therapist': forms.Select(attrs={'class': 'form-control'}),
            'booking_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'booking_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ご質問やご要望があればお書きください'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # アクティブなサービスのみを選択肢に表示
        self.fields['service'].queryset = Service.objects.filter(is_active=True)
        
        # アクティブな施術者のみを選択肢に表示
        therapist_choices = [('', '指名なし（どなたでも）')]
        active_therapists = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
        for therapist in active_therapists:
            label = f"{therapist.display_name}"
            if therapist.experience_years > 0:
                label += f" (経験{therapist.experience_years}年)"
            therapist_choices.append((therapist.id, label))
        
        self.fields['therapist'].choices = therapist_choices
        self.fields['therapist'].required = False
        
        # 必須フィールドの設定
        self.fields['notes'].required = False
    
    def clean_customer_email(self):
        email = self.cleaned_data['customer_email']
        
        # 本日の同一メールアドレスでの予約数をチェック
        today = timezone.now().date()
        daily_bookings = Booking.objects.filter(
            customer__email=email,
            created_at__date=today
        ).count()
        
        # getattr を使用して設定値を安全に取得
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
        
        # getattr を使用して設定値を安全に取得
        daily_limit = getattr(settings, 'BOOKING_DAILY_LIMIT_PER_PHONE', 2)
        
        if daily_bookings >= daily_limit:
            raise ValidationError(
                f'申し訳ございません。同一電話番号での1日の予約は{daily_limit}件までとさせていただいております。'
            )
        
        return phone
    
    def clean_booking_date(self):
        booking_date = self.cleaned_data['booking_date']
        
        # 過去の日付は選択不可
        if booking_date < timezone.now().date():
            raise ValidationError('過去の日付は選択できません。')
        
        # 3ヶ月先までの予約に制限
        max_date = timezone.now().date() + datetime.timedelta(days=90)
        if booking_date > max_date:
            raise ValidationError('予約は3ヶ月先までとなっております。')
        
        return booking_date
    
    def clean_booking_time(self):
        booking_time = self.cleaned_data['booking_time']
        
        # 営業時間のチェック（例：9:00-20:00）
        if booking_time < datetime.time(9, 0) or booking_time > datetime.time(20, 0):
            raise ValidationError('営業時間は9:00-20:00です。')
        
        return booking_time
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        therapist = cleaned_data.get('therapist')
        
        # 同じ日時・施術者の予約がないかチェック
        if booking_date and booking_time:
            existing_booking_filter = {
                'booking_date': booking_date,
                'booking_time': booking_time,
                'status__in': ['pending', 'confirmed']
            }
            
            # 施術者が指定されている場合は同じ施術者の重複をチェック
            if therapist:
                existing_booking_filter['therapist'] = therapist
                error_message = f'申し訳ございません。{therapist.display_name}さんのこの日時は既に予約が入っております。'
            else:
                # 施術者指定なしの場合は、指定なしの予約が既にあるかチェック
                existing_booking_filter['therapist__isnull'] = True
                error_message = '申し訳ございません。この日時は既に予約が入っております。'
            
            existing_booking = Booking.objects.filter(**existing_booking_filter).exists()
            
            if existing_booking:
                raise ValidationError(error_message + '別の時間をお選びください。')
        
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
        
        # 承認が必要な場合はpendingステータスに設定
        if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True):
            booking.status = 'pending'
        else:
            booking.status = 'confirmed'
        
        if commit:
            booking.save()
        
        return booking