from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
import datetime
import json
import logging

from .models import Service, Therapist, Booking, Customer, BusinessHours, BookingSettings, Schedule
from .forms import ServiceSelectionForm, DateTimeTherapistForm, CustomerInfoForm, validate_booking_time_slot

logger = logging.getLogger(__name__)

def booking_step1(request):
    """ステップ1: サービス選択"""
    if request.method == 'POST':
        form = ServiceSelectionForm(request.POST)
        if form.is_valid():
            # セッションにサービス情報を保存
            request.session['booking_service_id'] = form.cleaned_data['service'].id
            return redirect('bookings:booking_step2')
    else:
        form = ServiceSelectionForm()
    
    context = {
        'form': form,
        'title': 'ステップ1: サービス選択 - GRACE SPA',
        'step': 1,
        'total_steps': 3
    }
    return render(request, 'bookings/step1_service.html', context)

def booking_step2(request):
    """ステップ2: 日時・施術者選択"""
    # セッションからサービス情報を取得
    service_id = request.session.get('booking_service_id')
    if not service_id:
        messages.error(request, 'サービスが選択されていません。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        messages.error(request, '選択されたサービスが見つかりません。')
        return redirect('bookings:booking_step1')
    
    # 施術者選択機能が有効かチェック
    try:
        booking_settings = BookingSettings.get_current_settings()
        enable_therapist_selection = booking_settings.enable_therapist_selection
    except:
        enable_therapist_selection = False
    
    if request.method == 'POST':
        form = DateTimeTherapistForm(request.POST, enable_therapist_selection=enable_therapist_selection, service=service)
        if form.is_valid():
            # 施術者情報を処理
            therapist_value = form.cleaned_data.get('therapist')
            if therapist_value and therapist_value != 'none':
                request.session['booking_therapist_id'] = therapist_value.id
            else:
                request.session['booking_therapist_id'] = None
            
            request.session['booking_date'] = form.cleaned_data['booking_date'].isoformat()
            request.session['booking_time'] = form.cleaned_data['booking_time'].strftime('%H:%M')
            request.session['booking_notes'] = form.cleaned_data['notes']
            return redirect('bookings:booking_step3')
    else:
        form = DateTimeTherapistForm(enable_therapist_selection=enable_therapist_selection, service=service)
    
    # 施術者一覧（設定が有効な場合のみ）
    therapists = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name') if enable_therapist_selection else []
    
    # 営業時間を取得
    business_hours = {}
    for bh in BusinessHours.objects.all():
        business_hours[bh.weekday] = {
            'is_open': bh.is_open,
            'open_time': bh.open_time,
            'close_time': bh.close_time,
            'last_booking_time': bh.last_booking_time
        }
    
    context = {
        'form': form,
        'service': service,
        'therapists': therapists,
        'enable_therapist_selection': enable_therapist_selection,
        'business_hours': json.dumps(business_hours, default=str),
        'title': 'ステップ2: 日時選択 - GRACE SPA',
        'step': 2,
        'total_steps': 3
    }
    return render(request, 'bookings/step2_datetime.html', context)

def booking_step3(request):
    """ステップ3: お客様情報入力"""
    # セッションから情報を取得
    service_id = request.session.get('booking_service_id')
    therapist_id = request.session.get('booking_therapist_id')
    booking_date = request.session.get('booking_date')
    booking_time = request.session.get('booking_time')
    notes = request.session.get('booking_notes', '')
    
    if not all([service_id, booking_date, booking_time]):
        messages.error(request, '予約情報が不完全です。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=service_id)
        therapist = Therapist.objects.get(id=therapist_id) if therapist_id else None
    except (Service.DoesNotExist, Therapist.DoesNotExist):
        messages.error(request, '選択された情報が見つかりません。')
        return redirect('bookings:booking_step1')
    
    if request.method == 'POST':
        form = CustomerInfoForm(request.POST)
        if form.is_valid():
            # セッションに顧客情報を保存
            request.session['customer_name'] = form.cleaned_data['customer_name']
            request.session['customer_email'] = form.cleaned_data['customer_email']
            request.session['customer_phone'] = form.cleaned_data['customer_phone']
            return redirect('bookings:booking_confirm')
    else:
        form = CustomerInfoForm()
    
    context = {
        'form': form,
        'service': service,
        'therapist': therapist,
        'booking_date': datetime.datetime.fromisoformat(booking_date).date(),
        'booking_time': datetime.datetime.strptime(booking_time, '%H:%M').time(),
        'notes': notes,
        'title': 'ステップ3: お客様情報入力 - GRACE SPA',
        'step': 3,
        'total_steps': 3
    }
    return render(request, 'bookings/step3_customer.html', context)

def booking_confirm(request):
    """予約確認画面"""
    # セッションから全情報を取得
    session_data = {
        'service_id': request.session.get('booking_service_id'),
        'therapist_id': request.session.get('booking_therapist_id'),
        'booking_date': request.session.get('booking_date'),
        'booking_time': request.session.get('booking_time'),
        'notes': request.session.get('booking_notes', ''),
        'customer_name': request.session.get('customer_name'),
        'customer_email': request.session.get('customer_email'),
        'customer_phone': request.session.get('customer_phone'),
    }
    
    # 必要な情報がすべて揃っているかチェック
    required_fields = ['service_id', 'booking_date', 'booking_time', 'customer_name', 'customer_email', 'customer_phone']
    if not all(session_data.get(field) for field in required_fields):
        messages.error(request, '予約情報が不完全です。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=session_data['service_id'])
        therapist = Therapist.objects.get(id=session_data['therapist_id']) if session_data['therapist_id'] else None
        booking_date = datetime.datetime.fromisoformat(session_data['booking_date']).date()
        booking_time = datetime.datetime.strptime(session_data['booking_time'], '%H:%M').time()
    except (Service.DoesNotExist, Therapist.DoesNotExist, ValueError):
        messages.error(request, '予約情報に問題があります。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    # 予約可能性をチェック（表示時のみ - 実際の予約確定は後で行う）
    validation_error = None
    try:
        validate_booking_time_slot(service, booking_date, booking_time, therapist)
    except ValidationError as e:
        validation_error = str(e)
        logger.warning(f"予約時間重複チェック: {validation_error}")
    
    if request.method == 'POST':
        # 予約を確定する前に再度チェック
        try:
            # 最終的な重複チェック
            validate_booking_time_slot(service, booking_date, booking_time, therapist)
            
            # 顧客情報を取得または作成
            customer, created = Customer.objects.get_or_create(
                email=session_data['customer_email'],
                defaults={
                    'name': session_data['customer_name'],
                    'phone': session_data['customer_phone']
                }
            )
            
            # 既存顧客の場合は情報を更新
            if not created:
                customer.name = session_data['customer_name']
                customer.phone = session_data['customer_phone']
                customer.save()
            
            # 予約を作成
            booking = Booking.objects.create(
                customer=customer,
                service=service,
                therapist=therapist,
                booking_date=booking_date,
                booking_time=booking_time,
                notes=session_data['notes'],
                status='pending' if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True) else 'confirmed'
            )
            
            # メール通知を送信
            try:
                send_booking_notification_emails(booking)
                if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True):
                    messages.success(
                        request, 
                        '予約申込みを受け付けました。管理者が確認後、確定のご連絡をいたします。'
                    )
                else:
                    messages.success(request, '予約が確定しました。')
            except Exception as e:
                logger.error(f"メール送信エラー: {e}")
                messages.success(request, '予約申込みを受け付けました。')
            
            # セッションをクリア
            session_keys = ['booking_service_id', 'booking_therapist_id', 'booking_date', 'booking_time', 
                          'booking_notes', 'customer_name', 'customer_email', 'customer_phone']
            for key in session_keys:
                request.session.pop(key, None)
            
            return redirect('bookings:booking_complete')
            
        except ValidationError as e:
            # エラーメッセージを設定して確認画面を再表示
            messages.error(request, str(e))
            validation_error = str(e)
            logger.warning(f"予約確定時エラー: {validation_error}")
            
        except Exception as e:
            messages.error(request, f'予約の作成中にエラーが発生しました: {str(e)}')
            logger.error(f"予約作成エラー: {str(e)}")
    
    context = {
        'service': service,
        'therapist': therapist,
        'booking_date': booking_date,
        'booking_time': booking_time,
        'notes': session_data['notes'],
        'customer_name': session_data['customer_name'],
        'customer_email': session_data['customer_email'],
        'customer_phone': session_data['customer_phone'],
        'validation_error': validation_error,  # テンプレートでのエラー表示用
        'title': '予約確認 - GRACE SPA'
    }
    return render(request, 'bookings/confirm.html', context)

def booking_complete(request):
    """予約完了画面"""
    context = {
        'title': '予約完了 - GRACE SPA'
    }
    return render(request, 'bookings/complete.html', context)

def get_available_times(request):
    """AJAX: 指定された日付の利用可能時間を取得（予定も含む）"""
    date_str = request.GET.get('date')
    therapist_id = request.GET.get('therapist_id')
    service_id = request.GET.get('service_id')
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
    
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        service = Service.objects.get(id=service_id) if service_id else None
    except (ValueError, Service.DoesNotExist):
        return JsonResponse({'error': 'Invalid date or service'}, status=400)
    
    # 営業時間を取得
    weekday = date.weekday()
    try:
        business_hour = BusinessHours.objects.get(weekday=weekday)
        if not business_hour.is_open:
            return JsonResponse({'available_times': []})
    except BusinessHours.DoesNotExist:
        return JsonResponse({'available_times': []})
    
    # 予約設定を取得
    try:
        booking_settings = BookingSettings.get_current_settings()
        interval_minutes = booking_settings.booking_interval_minutes
        buffer_minutes = booking_settings.treatment_buffer_minutes
    except:
        interval_minutes = 10  # デフォルト10分刻み
        buffer_minutes = 15   # デフォルト15分インターバル
    
    # 指定日の既存予約を取得
    existing_bookings = Booking.objects.filter(
        booking_date=date,
        status__in=['pending', 'confirmed']
    )
    
    # 施術者が指定されている場合は、その施術者の予約をチェック
    if therapist_id and therapist_id != 'none':
        existing_bookings = existing_bookings.filter(therapist_id=therapist_id)
    else:
        # 施術者指定なしの場合は、指定なしの予約のみチェック
        existing_bookings = existing_bookings.filter(therapist__isnull=True)
    
    # 指定日の既存予定を取得
    try:
        existing_schedules = Schedule.objects.filter(
            schedule_date=date,
            is_active=True
        )
        
        # 施術者が指定されている場合は、その施術者の予定または全体予定をチェック
        if therapist_id and therapist_id != 'none':
            existing_schedules = existing_schedules.filter(
                Q(therapist_id=therapist_id) | Q(therapist__isnull=True)
            )
        # 施術者指定なしの場合は、全体予定のみチェック
        else:
            existing_schedules = existing_schedules.filter(therapist__isnull=True)
    except:
        existing_schedules = []
    
    # 利用可能時間を計算
    available_times = []
    current_time = business_hour.open_time
    
    while current_time <= business_hour.last_booking_time:
        # 新規予約の時間帯を計算
        if service:
            new_booking_start = datetime.datetime.combine(date, current_time)
            new_booking_end = new_booking_start + datetime.timedelta(minutes=service.duration_minutes + buffer_minutes)
        else:
            new_booking_start = datetime.datetime.combine(date, current_time)
            new_booking_end = new_booking_start + datetime.timedelta(minutes=60 + buffer_minutes)  # デフォルト60分
        
        # 既存予約との重複チェック
        is_available = True
        for existing_booking in existing_bookings:
            existing_start = datetime.datetime.combine(date, existing_booking.booking_time)
            existing_end = existing_start + datetime.timedelta(
                minutes=existing_booking.service.duration_minutes + buffer_minutes
            )
            
            # 時間帯が重複するかチェック
            if (new_booking_start < existing_end and new_booking_end > existing_start):
                is_available = False
                break
        
        # 既存予定との重複チェック
        if is_available:
            for existing_schedule in existing_schedules:
                schedule_start = datetime.datetime.combine(date, existing_schedule.start_time)
                schedule_end = datetime.datetime.combine(date, existing_schedule.end_time)
                
                # 予約時間が予定時間と重複するかチェック
                if (new_booking_start < schedule_end and new_booking_end > schedule_start):
                    is_available = False
                    break
        
        if is_available:
            available_times.append(current_time.strftime('%H:%M'))
        
        # 次の時間帯へ
        current_time = (datetime.datetime.combine(date, current_time) + 
                       datetime.timedelta(minutes=interval_minutes)).time()
    
    return JsonResponse({'available_times': available_times})

# ===== メール送信機能 =====

def send_booking_notification_emails(booking):
    """予約通知メール送信"""
    # 顧客への通知メール
    send_customer_notification_email(booking)
    
    # 管理者への通知メール
    send_admin_notification_email(booking)

def send_customer_notification_email(booking):
    """顧客への予約通知メール"""
    if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True):
        subject = f'【GRACE SPA】予約申込み受付確認 - {booking.booking_date}'
        status_text = '申込み受付'
        next_step = 'スタッフが確認後、確定のご連絡をいたします。'
    else:
        subject = f'【GRACE SPA】予約確定 - {booking.booking_date}'
        status_text = '確定'
        next_step = '当日お会いできることを楽しみにしております。'
    
    message = f"""
{booking.customer.name} 様

この度は、GRACE SPAにご予約をいただき、ありがとうございます。
以下の内容で予約{status_text}いたしました。

■ 予約内容
予約番号: #{booking.id}
お客様名: {booking.customer.name}
サービス: {booking.service.name}
日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}
ステータス: {booking.get_status_display()}

■ お客様情報
メールアドレス: {booking.customer.email}
電話番号: {booking.customer.phone}
"""

    if booking.notes:
        message += f"""
ご要望・備考: {booking.notes}
"""

    message += f"""

■ 注意事項
・当店は完全予約制です
・ご予約時間の5分前にお越しください
・10分以上の遅刻をされた場合、足湯サービスができない場合があります
・当日キャンセル・無断キャンセルはキャンセル料が発生する場合があります

{next_step}

ご不明な点がございましたら、お気軽にお問い合わせください。

GRACE SPA
"""
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.customer.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"顧客メール送信エラー: {e}")

def send_admin_notification_email(booking):
    """管理者への予約通知メール"""
    subject = f'【GRACE SPA管理】新規予約申込み - {booking.booking_date} {booking.booking_time}'
    
    message = f"""
新しい予約申込みがありました。

■ 予約詳細
予約番号: #{booking.id}
申込日時: {booking.created_at.strftime('%Y年%m月%d日 %H:%M')}

■ 顧客情報
お名前: {booking.customer.name}
メールアドレス: {booking.customer.email}
電話番号: {booking.customer.phone}

■ 予約内容
サービス: {booking.service.name}
希望日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}
現在のステータス: {booking.get_status_display()}
"""

    if booking.notes:
        message += f"""
ご要望・備考: {booking.notes}
"""

    if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True):
        message += f"""

■ 対応が必要な作業
1. 顧客情報の確認
2. 予約枠の最終確認
3. 管理画面での予約承認
4. 顧客への確定通知
"""

    message += """

管理画面: http://localhost:8000/admin/
"""
    
    # 管理者メールアドレスの設定
    admin_emails = getattr(settings, 'BOOKING_ADMIN_EMAILS', [settings.DEFAULT_FROM_EMAIL])
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"管理者メール送信エラー: {e}")