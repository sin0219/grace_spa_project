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

# メール機能のインポート
from emails.utils import (
    send_booking_confirmation_email,
    send_admin_new_booking_email,
    send_booking_cancelled_email
)

logger = logging.getLogger(__name__)

def booking_step1(request):
    """ステップ1: サービス選択"""
    
    # デバッグ: サービス情報を確認
    all_services = Service.objects.all()
    active_services = Service.objects.filter(is_active=True)
    
    logger.debug(f"全サービス数: {all_services.count()}")
    logger.debug(f"アクティブサービス数: {active_services.count()}")
    
    for service in all_services:
        logger.debug(f"サービス: {service.name}, アクティブ: {service.is_active}, ID: {service.id}")
    
    if request.method == 'POST':
        form = ServiceSelectionForm(request.POST)
        logger.debug(f"POSTデータ: {request.POST}")
        logger.debug(f"フォームが有効: {form.is_valid()}")
        if not form.is_valid():
            logger.debug(f"フォームエラー: {form.errors}")
            
        if form.is_valid():
            # セッションにサービス情報を保存
            service_id = form.cleaned_data['service'].id
            logger.debug(f"選択されたサービスID: {service_id}")
            request.session['booking_service_id'] = service_id
            return redirect('bookings:booking_step2')
    else:
        form = ServiceSelectionForm()
    
    services = Service.objects.filter(is_active=True).order_by('name')
    logger.debug(f"テンプレートに渡すサービス数: {services.count()}")
    
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
    
    # 施術者選択機能が有効かチェック
    try:
        booking_settings = BookingSettings.get_current_settings()
        enable_therapist_selection = booking_settings.enable_therapist_selection
    except:
        enable_therapist_selection = True  # デフォルトは有効
    
    if request.method == 'POST':
        form = DateTimeTherapistForm(request.POST, enable_therapist_selection=enable_therapist_selection)
        if form.is_valid():
            # セッションに選択情報を保存
            request.session['booking_date'] = form.cleaned_data['booking_date'].isoformat()
            request.session['booking_time'] = form.cleaned_data['booking_time'].strftime('%H:%M')
            
            if enable_therapist_selection:
                therapist = form.cleaned_data.get('therapist')
                request.session['booking_therapist_id'] = therapist.id if therapist else None
            else:
                request.session['booking_therapist_id'] = None
            
            return redirect('bookings:booking_step3')
    else:
        form = DateTimeTherapistForm(enable_therapist_selection=enable_therapist_selection)
    
    # アクティブな施術者を取得
    therapists = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'form': form,
        'service': service,
        'therapists': therapists,
        'enable_therapist_selection': enable_therapist_selection,
        'title': 'ステップ2: 日時・施術者選択 - GRACE SPA',
        'step': 2,
        'total_steps': 3
    }
    return render(request, 'bookings/step2_datetime.html', context)

def booking_step3(request):
    """ステップ3: お客様情報入力"""
    # セッションから予約情報を取得
    service_id = request.session.get('booking_service_id')
    booking_date_str = request.session.get('booking_date')
    booking_time_str = request.session.get('booking_time')
    therapist_id = request.session.get('booking_therapist_id')
    
    if not all([service_id, booking_date_str, booking_time_str]):
        messages.error(request, '予約情報が不完全です。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=service_id)
        booking_date = datetime.datetime.fromisoformat(booking_date_str).date()
        booking_time = datetime.datetime.strptime(booking_time_str, '%H:%M').time()
        therapist = Therapist.objects.get(id=therapist_id) if therapist_id else None
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
        form = CustomerInfoForm(request.POST)
        if form.is_valid():
            # セッションに顧客情報を保存
            request.session['customer_name'] = form.cleaned_data['name']
            request.session['customer_email'] = form.cleaned_data['email']
            request.session['customer_phone'] = form.cleaned_data['phone']
            request.session['booking_notes'] = form.cleaned_data['notes']
            
            return redirect('bookings:booking_confirm')
    else:
        form = CustomerInfoForm()
    
    context = {
        'form': form,
        'service': service,
        'therapist': therapist,
        'booking_date': booking_date,
        'booking_time': booking_time,
        'validation_error': validation_error,
        'title': 'ステップ3: お客様情報入力 - GRACE SPA',
        'step': 3,
        'total_steps': 3
    }
    return render(request, 'bookings/step3_customer.html', context)

def booking_confirm(request):
    """確認画面"""
    # セッションからすべての情報を取得
    session_keys = ['booking_service_id', 'booking_date', 'booking_time', 'booking_therapist_id',
                   'customer_name', 'customer_email', 'customer_phone', 'booking_notes']
    
    session_data = {}
    for key in session_keys:
        session_data[key] = request.session.get(key)
    
    # 必須項目のチェック
    if not all([session_data['booking_service_id'], session_data['booking_date'], 
               session_data['booking_time'], session_data['customer_name'], 
               session_data['customer_email']]):
        messages.error(request, '予約情報が不完全です。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=session_data['booking_service_id'])
        booking_date = datetime.datetime.fromisoformat(session_data['booking_date']).date()
        booking_time = datetime.datetime.strptime(session_data['booking_time'], '%H:%M').time()
        therapist = Therapist.objects.get(id=session_data['booking_therapist_id']) if session_data['booking_therapist_id'] else None
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
                notes=session_data['booking_notes'],
                status='pending' if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True) else 'confirmed'
            )
            
            # メール通知を送信
            try:
                # 顧客向け予約確認メール
                send_booking_confirmation_email(booking)
                
                # 管理者向け新規予約通知メール
                send_admin_new_booking_email(booking)
                
                if getattr(settings, 'BOOKING_REQUIRES_APPROVAL', True):
                    messages.success(
                        request, 
                        '予約申込みを受け付けました。管理者が確認後、確定のご連絡をいたします。'
                    )
                else:
                    messages.success(request, '予約が確定しました。')
                    
                logger.info(f"新規予約作成とメール送信完了: {booking}")
                    
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
            messages.error(request, f'予約の確定に失敗しました: {str(e)}')
            logger.error(f"予約確定エラー: {str(e)}")
        except Exception as e:
            messages.error(request, '予約の確定中にエラーが発生しました。もう一度お試しください。')
            logger.error(f"予約確定エラー: {str(e)}")
    
    context = {
        'service': service,
        'therapist': therapist,
        'booking_date': booking_date,
        'booking_time': booking_time,
        'customer_name': session_data['customer_name'],
        'customer_email': session_data['customer_email'],
        'customer_phone': session_data['customer_phone'],
        'notes': session_data['booking_notes'],
        'validation_error': validation_error,
        'title': '予約確認 - GRACE SPA'
    }
    return render(request, 'bookings/confirm.html', context)

def booking_complete(request):
    """完了画面"""
    context = {
        'title': '予約完了 - GRACE SPA'
    }
    return render(request, 'bookings/complete.html', context)

def get_available_times(request):
    """AJAX: 指定された日付の利用可能時間を取得（修正版）"""
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    therapist_id = request.GET.get('therapist_id')
    
    if not date_str or not service_id:
        return JsonResponse({'error': 'パラメータが不足しています'}, status=400)
    
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        service = Service.objects.get(id=service_id)
        therapist = Therapist.objects.get(id=therapist_id) if therapist_id else None
    except (ValueError, Service.DoesNotExist, Therapist.DoesNotExist):
        return JsonResponse({'error': '無効なパラメータです'}, status=400)
    
    # 営業時間を取得（weekdayフィールドを使用）
    try:
        business_hours = BusinessHours.objects.filter(
            weekday=date.weekday(),  # day_of_week → weekday に修正
            is_open=True
        ).first()
        
        if not business_hours:
            return JsonResponse({'available_times': []})
        
        # 予約設定を取得
        try:
            booking_settings = BookingSettings.get_current_settings()
            interval_minutes = booking_settings.booking_interval_minutes
        except:
            interval_minutes = 10  # デフォルトを10分に変更
        
        # 利用可能な時間スロットを生成
        available_times = []
        current_time = business_hours.open_time
        
        while current_time <= business_hours.last_booking_time:
            # この時間に予約が可能かチェック
            try:
                validate_booking_time_slot(service, date, current_time, therapist)
                available_times.append(current_time.strftime('%H:%M'))
            except ValidationError:
                pass
            
            # 設定された間隔で次の時間へ
            current_datetime = datetime.datetime.combine(date, current_time)
            current_datetime += datetime.timedelta(minutes=interval_minutes)
            current_time = current_datetime.time()
        
        return JsonResponse({'available_times': available_times})
        
    except Exception as e:
        logger.error(f"利用可能時間取得エラー: {str(e)}")
        return JsonResponse({'error': 'サーバーエラーが発生しました'}, status=500)


# ===============================
# 予約管理機能（キャンセル処理など）
# ===============================

def cancel_booking(request, booking_id):
    """予約キャンセル処理"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # キャンセル可能かチェック（例：予約日の前日まで）
    if booking.booking_date <= timezone.now().date():
        messages.error(request, '当日・過去の予約はキャンセルできません。')
        return redirect('dashboard:booking_list')
    
    if request.method == 'POST':
        old_status = booking.status
        booking.status = 'cancelled'
        booking.save()
        
        try:
            # キャンセル通知メール送信
            send_booking_cancelled_email(booking, cancelled_by_customer=False)
            messages.success(request, f'{booking.customer.name}様の予約をキャンセルしました。')
            logger.info(f"予約キャンセル処理完了: {booking}")
        except Exception as e:
            logger.error(f"キャンセルメール送信エラー: {e}")
            messages.success(request, f'{booking.customer.name}様の予約をキャンセルしました。')
        
        return redirect('dashboard:booking_list')
    
    context = {
        'booking': booking,
        'title': '予約キャンセル確認'
    }
    return render(request, 'dashboard/booking_cancel.html', context)


def confirm_booking(request, booking_id):
    """予約確定処理"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.status != 'pending':
        messages.error(request, 'この予約は既に処理済みです。')
        return redirect('dashboard:booking_list')
    
    if request.method == 'POST':
        old_status = booking.status
        booking.status = 'confirmed'
        booking.save()
        
        try:
            # ステータス変更通知メール送信（確定通知）
            from emails.utils import send_booking_status_changed_email
            send_booking_status_changed_email(booking, old_status, 'confirmed')
            messages.success(request, f'{booking.customer.name}様の予約を確定しました。')
            logger.info(f"予約確定処理完了: {booking}")
        except Exception as e:
            logger.error(f"確定メール送信エラー: {e}")
            messages.success(request, f'{booking.customer.name}様の予約を確定しました。')
        
        return redirect('dashboard:booking_detail', booking_id=booking.id)
    
    context = {
        'booking': booking,
        'title': '予約確定確認'
    }
    return render(request, 'dashboard/booking_confirm.html', context)


def complete_booking(request, booking_id):
    """施術完了処理"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.status not in ['confirmed', 'pending']:
        messages.error(request, 'この予約は施術完了にできません。')
        return redirect('dashboard:booking_list')
    
    if request.method == 'POST':
        old_status = booking.status
        booking.status = 'completed'
        booking.save()
        
        try:
            # ステータス変更通知メール送信（完了通知）
            from emails.utils import send_booking_status_changed_email
            send_booking_status_changed_email(booking, old_status, 'completed')
            messages.success(request, f'{booking.customer.name}様の施術を完了にしました。')
            logger.info(f"施術完了処理: {booking}")
        except Exception as e:
            logger.error(f"完了メール送信エラー: {e}")
            messages.success(request, f'{booking.customer.name}様の施術を完了にしました。')
        
        return redirect('dashboard:booking_detail', booking_id=booking.id)
    
    context = {
        'booking': booking,
        'title': '施術完了確認'
    }
    return render(request, 'dashboard/booking_complete.html', context)


# ===============================
# 古い送信メール関数（後方互換性のため残す）
# ===============================

def send_booking_notification_emails(booking):
    """
    後方互換性のための関数
    新しいメール機能に置き換え
    """
    try:
        # 新しいメール機能を使用
        send_booking_confirmation_email(booking)
        send_admin_new_booking_email(booking)
        return True
    except Exception as e:
        logger.error(f"メール送信エラー（互換関数）: {e}")
        return False