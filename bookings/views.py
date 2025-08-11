from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError  # 追加
from django.db.models import Q  # 追加
from .forms import ServiceSelectionForm, DateTimeTherapistForm, CustomerInfoForm
from .models import Service, Booking, Customer, Therapist, BusinessHours, Schedule
import datetime
import json

# ===== 3ステップ予約システム =====

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
    
    services = Service.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'services': services,
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
    
    # 予約設定を取得
    from .models import BookingSettings
    try:
        booking_settings = BookingSettings.get_current_settings()
        enable_therapist_selection = booking_settings.enable_therapist_selection
    except:
        enable_therapist_selection = True  # デフォルトは有効
    
    if request.method == 'POST':
        form = DateTimeTherapistForm(request.POST)
        if form.is_valid():
            # セッションに情報を保存
            therapist_value = form.cleaned_data['therapist']
            if enable_therapist_selection and therapist_value:
                request.session['booking_therapist_id'] = therapist_value.id
            else:
                request.session['booking_therapist_id'] = None
            
            request.session['booking_date'] = form.cleaned_data['booking_date'].isoformat()
            request.session['booking_time'] = form.cleaned_data['booking_time'].strftime('%H:%M')
            request.session['booking_notes'] = form.cleaned_data['notes']
            return redirect('bookings:booking_step3')
    else:
        form = DateTimeTherapistForm()
    
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
        'enable_therapist_selection': enable_therapist_selection,  # 新規追加
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
    
    if request.method == 'POST':
        # 予約を確定
        try:
            # 最終的な重複チェック（フォームバリデーション）
            from .forms import validate_booking_time_slot
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
                print(f"メール送信エラー: {e}")
                messages.success(request, '予約申込みを受け付けました。')
            
            # セッションをクリア
            session_keys = ['booking_service_id', 'booking_therapist_id', 'booking_date', 'booking_time', 
                          'booking_notes', 'customer_name', 'customer_email', 'customer_phone']
            for key in session_keys:
                request.session.pop(key, None)
            
            return redirect('bookings:booking_complete')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'予約の作成中にエラーが発生しました: {str(e)}')
    
    context = {
        'service': service,
        'therapist': therapist,
        'booking_date': booking_date,
        'booking_time': booking_time,
        'notes': session_data['notes'],
        'customer_name': session_data['customer_name'],
        'customer_email': session_data['customer_email'],
        'customer_phone': session_data['customer_phone'],
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
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
    
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # 営業時間を取得
    weekday = date.weekday()
    try:
        business_hour = BusinessHours.objects.get(weekday=weekday)
        if not business_hour.is_open:
            return JsonResponse({'available_times': []})
    except BusinessHours.DoesNotExist:
        return JsonResponse({'available_times': []})
    
    # 予約設定を取得
    from .models import BookingSettings
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
    if therapist_id:
        existing_bookings = existing_bookings.filter(therapist_id=therapist_id)
    else:
        # 施術者指定なしの場合は、指定なしの予約のみチェック
        existing_bookings = existing_bookings.filter(therapist__isnull=True)
    
    # 指定日の既存予定を取得（新規追加）
    try:
        existing_schedules = Schedule.objects.filter(
            schedule_date=date,
            is_active=True
        )
        
        # 施術者が指定されている場合は、その施術者の予定または全体予定をチェック
        if therapist_id:
            existing_schedules = existing_schedules.filter(
                Q(therapist_id=therapist_id) | Q(therapist__isnull=True)
            )
        # 施術者指定なしの場合は、全体予定のみチェック
        else:
            existing_schedules = existing_schedules.filter(therapist__isnull=True)
    except:
        existing_schedules = []
    
    # 予約不可時間帯を計算
    blocked_times = set()
    
    # 既存予約による不可時間
    for booking in existing_bookings:
        # 予約開始時間
        booking_start = datetime.datetime.combine(date, booking.booking_time)
        
        # 施術終了時間 + インターバル
        service_duration = booking.service.duration_minutes
        total_blocked_duration = service_duration + buffer_minutes
        
        # ブロックされる時間帯を10分刻みで計算
        current_time = booking_start
        end_time = booking_start + datetime.timedelta(minutes=total_blocked_duration)
        
        while current_time < end_time:
            blocked_times.add(current_time.time())
            current_time += datetime.timedelta(minutes=interval_minutes)
    
    # 既存予定による不可時間（新規追加）
    for schedule in existing_schedules:
        # 予定開始時間から終了時間まで
        schedule_start = datetime.datetime.combine(date, schedule.start_time)
        schedule_end = datetime.datetime.combine(date, schedule.end_time)
        
        # ブロックされる時間帯を10分刻みで計算
        current_time = schedule_start
        
        while current_time < schedule_end:
            blocked_times.add(current_time.time())
            current_time += datetime.timedelta(minutes=interval_minutes)
    
    # 10分刻みの時間スロットを生成
    available_times = []
    current_time = datetime.datetime.combine(date, business_hour.open_time)
    end_time = datetime.datetime.combine(date, business_hour.last_booking_time)
    
    while current_time <= end_time:
        time_str = current_time.strftime('%H:%M')
        is_available = current_time.time() not in blocked_times
        
        available_times.append({
            'time': time_str,
            'available': is_available
        })
        
        current_time += datetime.timedelta(minutes=interval_minutes)
    
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
        print(f"顧客メール送信エラー: {e}")

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
4. 必要に応じて顧客への確認電話

管理画面: /dashboard/
"""
    else:
        message += f"""

■ 確認事項
管理画面で詳細を確認してください
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [getattr(settings, 'ADMIN_EMAIL', 'admin@gracespa.com')],
            fail_silently=False,
        )
    except Exception as e:
        print(f"管理者メール送信エラー: {e}")

def send_booking_confirmation_email(booking):
    """予約確定メール送信（管理者が承認時に使用）"""
    subject = f'【GRACE SPA】予約確定のお知らせ - {booking.booking_date}'
    
    message = f"""
{booking.customer.name} 様

お申込みいただいた予約が確定いたしました。

■ 確定した予約内容
予約番号: #{booking.id}
お客様名: {booking.customer.name}
サービス: {booking.service.name}
日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}

■ 注意事項
・ご予約時間の5分前にお越しください
・10分以上の遅刻をされた場合、足湯サービスができない場合があります

当日お会いできることを楽しみにしております。

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
        print(f"確定メール送信エラー: {e}")