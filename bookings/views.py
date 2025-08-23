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
from .utils.language import get_language

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
    
    services = Service.objects.filter(is_active=True).order_by('sort_order', 'name')
    logger.debug(f"テンプレートに渡すサービス数: {services.count()}")
    
# ★ 常に日本語版テンプレートを使用
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
            
            # ステップ2の備考をセッションに保存
            request.session['booking_notes'] = form.cleaned_data.get('notes', '')
            
            return redirect('bookings:booking_step3')
    else:
        form = DateTimeTherapistForm(enable_therapist_selection=enable_therapist_selection)
    
    # アクティブな施術者を取得
    therapists = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
    
   # ★ 常に日本語版テンプレートを使用
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
            # セッションに顧客情報を保存（フィールド名を修正）
            request.session['customer_name'] = form.cleaned_data['customer_name']
            request.session['customer_email'] = form.cleaned_data['customer_email']
            request.session['customer_phone'] = form.cleaned_data['customer_phone']
            
            # ★ 新規追加: 性別と初回利用フラグをセッションに保存
            request.session['customer_gender'] = form.cleaned_data['gender']
            request.session['customer_is_first_visit'] = form.cleaned_data['is_first_visit']

            # ステップ2とステップ3の備考を統合
            step2_notes = request.session.get('booking_notes', '')
            step3_notes = form.cleaned_data.get('notes', '')
            
            # 両方に内容がある場合は改行で区切って統合
            combined_notes = []
            if step2_notes.strip(): 
                combined_notes.append(f"【ご要望】{step2_notes.strip()}")
            if step3_notes.strip():
                combined_notes.append(f"【備考】{step3_notes.strip()}")
            
            request.session['booking_notes'] = '\n'.join(combined_notes)
            
            return redirect('bookings:booking_confirm')
    else:
        form = CustomerInfoForm()
    
     # ★ 常に日本語版テンプレートを使用
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
    current_language = get_language()
    
    # ★ 修正: セッションからすべての情報を取得（性別と初回利用フラグを追加）
    session_keys = ['booking_service_id', 'booking_date', 'booking_time', 'booking_therapist_id',
                   'customer_name', 'customer_email', 'customer_phone', 'booking_notes',
                   'customer_gender', 'customer_is_first_visit']
    
    session_data = {}
    for key in session_keys:
        session_data[key] = request.session.get(key)
    
    # 必須項目のチェック
    if not all([session_data['booking_service_id'], session_data['booking_date'], 
               session_data['booking_time'], session_data['customer_name'], 
               session_data['customer_email']]):
        if current_language == 'en':
            messages.error(request, 'Booking information is incomplete. Please start over.')
        else:
            messages.error(request, '予約情報が不完全です。最初からやり直してください。')
        return redirect('bookings:booking_step1')
    
    try:
        service = Service.objects.get(id=session_data['booking_service_id'])
        booking_date = datetime.datetime.fromisoformat(session_data['booking_date']).date()
        booking_time = datetime.datetime.strptime(session_data['booking_time'], '%H:%M').time()
        therapist = Therapist.objects.get(id=session_data['booking_therapist_id']) if session_data['booking_therapist_id'] else None
    except (Service.DoesNotExist, Therapist.DoesNotExist, ValueError):
        if current_language == 'en':
            messages.error(request, 'There is a problem with the booking information. Please start over.')
        else:
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
            
            # ★ 修正: 顧客情報を取得または作成（性別と初回利用フラグを追加）
            customer, created = Customer.objects.get_or_create(
                email=session_data['customer_email'],
                defaults={
                    'name': session_data['customer_name'],
                    'phone': session_data['customer_phone'],
                    'gender': session_data['customer_gender'],
                    'is_first_visit': session_data['customer_is_first_visit']
                }
            )
            
            # ★ 修正: 既存顧客の場合は情報を更新（性別と初回利用フラグも更新）
            if not created:
                customer.name = session_data['customer_name']
                customer.phone = session_data['customer_phone']
                # ★ 注意: 既存顧客の性別は予約時の選択で上書きしない（管理者が手動で設定するため）
                # customer.gender = session_data['customer_gender']  # <- コメントアウト
                # is_first_visitは既存顧客なので常にFalseに設定
                customer.is_first_visit = False
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
                    if current_language == 'en':
                        messages.success(
                            request, 
                            'Your booking request has been received. We will contact you for confirmation after review by our staff.'
                        )
                    else:
                        messages.success(
                            request, 
                            '予約申込みを受け付けました。管理者が確認後、確定のご連絡をいたします。'
                        )
                else:
                    if current_language == 'en':
                        messages.success(request, 'Your booking has been confirmed.')
                    else:
                        messages.success(request, '予約が確定しました。')
                    
                logger.info(f"新規予約作成とメール送信完了: {booking}")
                    
            except Exception as e:
                logger.error(f"メール送信エラー: {e}")
                if current_language == 'en':
                    messages.success(request, 'Your booking request has been received.')
                else:
                    messages.success(request, '予約申込みを受け付けました。')
            
            # ★ 修正: セッションをクリア（性別と初回利用フラグも追加）
            session_keys = ['booking_service_id', 'booking_therapist_id', 'booking_date', 'booking_time', 
                          'booking_notes', 'customer_name', 'customer_email', 'customer_phone',
                          'customer_gender', 'customer_is_first_visit']
            for key in session_keys:
                request.session.pop(key, None)
            
            return redirect('bookings:booking_complete')
            
        except ValidationError as e:
            if current_language == 'en':
                messages.error(request, f'Failed to confirm booking: {str(e)}')
            else:
                messages.error(request, f'予約の確定に失敗しました: {str(e)}')
            logger.error(f"予約確定エラー: {str(e)}")
        except Exception as e:
            if current_language == 'en':
                messages.error(request, 'An error occurred while confirming your booking. Please try again.')
            else:
                messages.error(request, '予約の確定中にエラーが発生しました。もう一度お試しください。')
            logger.error(f"予約確定エラー: {str(e)}")
    
    # 言語に応じてコンテンツを分ける
    if current_language == 'en':
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
            'title': 'Booking Confirmation - GRACE SPA'
        }
        template_name = 'bookings/confirm_en.html'
    else:
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
        template_name = 'bookings/confirm.html'
    
    return render(request, template_name, context)

def booking_complete(request):
    """完了画面"""
    current_language = get_language()
    
    # 言語に応じてコンテンツを分ける
    if current_language == 'en':
        context = {
            'title': 'Booking Complete - GRACE SPA'
        }
        template_name = 'bookings/complete_en.html'
    else:
        context = {
            'title': '予約完了 - GRACE SPA'
        }
        template_name = 'bookings/complete.html'
    
    return render(request, template_name, context)

# bookings/views.py の最後に以下の英語版ビュー関数を追加してください

# ============ 英語版予約システム ============

def booking_step1_en(request):
    """Step 1: Service Selection (English)"""
    from .forms import ServiceSelectionForm
    from .models import Service
    
    if request.method == 'POST':
        form = ServiceSelectionForm(request.POST)
        if form.is_valid():
            # セッションに選択したサービスIDと言語を保存
            request.session['booking_service_id'] = form.cleaned_data['service'].id
            request.session['language'] = 'en'
            return redirect('bookings:booking_step2_en')
    else:
        form = ServiceSelectionForm()
    
    # アクティブなサービスを取得して英語版に変換
    services_data = Service.objects.filter(is_active=True).order_by('sort_order', 'name')
    services = []
    
    for service in services_data:
        services.append({
            'id': service.id,
            'name_en': service.get_name('en'),
            'description_en': service.get_description('en'),
            'duration_minutes': service.duration_minutes,
            'price': service.price,
            'is_active': service.is_active
        })
    
    context = {
        'form': form,
        'services': services,
        'title': 'Step 1: Service Selection - GRACE SPA',
        'step': 1,
        'total_steps': 3
    }
    return render(request, 'en/bookings/step1_service_en.html', context)


def booking_step2_en(request):
    """Step 2: Date & Therapist Selection (English)"""
    
    # セッションから予約情報を取得
    service_id = request.session.get('booking_service_id')
    if not service_id:
        messages.error(request, 'Service not selected. Please start over.')
        return redirect('bookings:booking_step1_en')
    
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        messages.error(request, 'Selected service not found.')
        return redirect('bookings:booking_step1_en')
    
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
            
            # ステップ2の備考をセッションに保存
            request.session['booking_notes'] = form.cleaned_data.get('notes', '')
            
            return redirect('bookings:booking_step3_en')
    else:
        form = DateTimeTherapistForm(enable_therapist_selection=enable_therapist_selection)
    
    # アクティブな施術者を取得して英語版に変換
    therapists_data = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
    therapists = []
    
    for therapist in therapists_data:
        therapists.append({
            'id': therapist.id,
            'display_name_en': therapist.get_display_name('en'),
            'description_en': therapist.get_description('en'),
            'image': therapist.image,
            'is_active': therapist.is_active
        })
    
    context = {
        'form': form,
        'service': {
            'id': service.id,
            'name_en': service.get_name('en'),
            'description_en': service.get_description('en'),
            'duration_minutes': service.duration_minutes,
            'price': service.price
        },
        'therapists': therapists,
        'enable_therapist_selection': enable_therapist_selection,
        'title': 'Step 2: Date & Therapist Selection - GRACE SPA',
        'step': 2,
        'total_steps': 3
    }
    return render(request, 'en/bookings/step2_datetime_en.html', context)


def booking_step3_en(request):
    """Step 3: Customer Information (English)"""
    
    # セッションから予約情報を取得
    service_id = request.session.get('booking_service_id')
    booking_date_str = request.session.get('booking_date')
    booking_time_str = request.session.get('booking_time')
    therapist_id = request.session.get('booking_therapist_id')
    
    if not all([service_id, booking_date_str, booking_time_str]):
        messages.error(request, 'Booking information is incomplete. Please start over.')
        return redirect('bookings:booking_step1_en')
    
    try:
        service = Service.objects.get(id=service_id)
        booking_date = datetime.datetime.fromisoformat(booking_date_str).date()
        booking_time = datetime.datetime.strptime(booking_time_str, '%H:%M').time()
        therapist = Therapist.objects.get(id=therapist_id) if therapist_id else None
    except (Service.DoesNotExist, Therapist.DoesNotExist, ValueError):
        messages.error(request, 'There is a problem with the booking information. Please start over.')
        return redirect('bookings:booking_step1_en')
    
    # 予約可能性をチェック（表示時のみ）
    validation_error = None
    try:
        validate_booking_time_slot(service, booking_date, booking_time, therapist)
    except ValidationError as e:
        validation_error = str(e)
        logger.warning(f"Booking time conflict check: {validation_error}")
    
    if request.method == 'POST':
        form = CustomerInfoForm(request.POST)
        if form.is_valid():
            # セッションに顧客情報を保存
            request.session['customer_name'] = form.cleaned_data['customer_name']
            request.session['customer_email'] = form.cleaned_data['customer_email']
            request.session['customer_phone'] = form.cleaned_data['customer_phone']
            request.session['customer_gender'] = form.cleaned_data['gender']
            request.session['customer_is_first_visit'] = form.cleaned_data['is_first_visit']

            # ステップ2とステップ3の備考を統合
            step2_notes = request.session.get('booking_notes', '')
            step3_notes = form.cleaned_data.get('notes', '')
            
            # 両方に内容がある場合は改行で区切って統合
            combined_notes = []
            if step2_notes.strip():
                combined_notes.append(f"【Requests】{step2_notes.strip()}")
            if step3_notes.strip():
                combined_notes.append(f"【Notes】{step3_notes.strip()}")
            
            request.session['booking_notes'] = '\n'.join(combined_notes)
            
            return redirect('bookings:booking_confirm_en')
    else:
        form = CustomerInfoForm()
    
    context = {
        'form': form,
        'service': {
            'id': service.id,
            'name_en': service.get_name('en'),
            'price': service.price
        },
        'therapist': {
            'display_name_en': therapist.get_display_name('en') if therapist else None
        } if therapist else None,
        'booking_date': booking_date,
        'booking_time': booking_time,
        'validation_error': validation_error,
        'title': 'Step 3: Customer Information - GRACE SPA',
        'step': 3,
        'total_steps': 3
    }
    return render(request, 'en/bookings/step3_customer_en.html', context)


def booking_confirm_en(request):
    """Booking Confirmation (English)"""
    # 英語版の確認画面
    # ... （詳細実装は次のステップで）...
    context = {
        'title': 'Booking Confirmation - GRACE SPA'
    }
    return render(request, 'en/bookings/confirm_en.html', context)


def booking_complete_en(request):
    """Booking Completion (English)"""
    # 英語版の完了画面
    # ... （詳細実装は次のステップで）...
    context = {
        'title': 'Booking Complete - GRACE SPA'
    }
    return render(request, 'en/bookings/complete_en.html', context)

def get_available_times(request):
    """AJAX: 指定された日付の利用可能時間を取得（①当日時刻チェック ②直前予約制限対応）"""
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    therapist_id = request.GET.get('therapist_id')
    
    if not date_str or not service_id:
        return JsonResponse({'error': 'パラメータが不足しています'}, status=400)
    
    try:
        booking_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        service = Service.objects.get(id=service_id)
        therapist = Therapist.objects.get(id=therapist_id) if therapist_id else None
    except (ValueError, Service.DoesNotExist, Therapist.DoesNotExist):
        return JsonResponse({'error': '無効なパラメータです'}, status=400)
    
    # 現在時刻を取得（aware datetime）
    now = timezone.now()
    current_date = now.date()
    is_today = booking_date == current_date
    
    # 営業時間を取得（weekdayフィールドを使用）
    try:
        business_hours = BusinessHours.objects.filter(
            weekday=booking_date.weekday(),
            is_open=True
        ).first()
        
        if not business_hours:
            return JsonResponse({'available_times': []})
        
        # 予約設定を取得
        try:
            settings_obj = BookingSettings.get_current_settings()
            interval_minutes = settings_obj.booking_interval_minutes
            buffer_minutes = settings_obj.treatment_buffer_minutes  # インターバル時間を取得
            # ②直前予約制限の設定を取得
            min_advance_minutes = getattr(settings_obj, 'min_advance_minutes', 20)  # デフォルト20分
        except:
            interval_minutes = 30  # デフォルト30分間隔
            buffer_minutes = 15   # デフォルト15分インターバル
            min_advance_minutes = 20  # デフォルト20分前まで
        
        # ①当日の場合の最小予約可能時間を計算
        min_booking_time = business_hours.open_time
        if is_today:
            # ②直前予約制限: 現在時刻 + 制限時間
            min_datetime = now + datetime.timedelta(minutes=min_advance_minutes)
            # 🔧 修正: ローカルタイムゾーンに変換してから時刻を取得
            from django.utils import timezone as django_timezone
            calculated_min_time = min_datetime.astimezone(django_timezone.get_current_timezone()).time()
            
            # 営業開始時間と比較して遅い方を採用
            if calculated_min_time > min_booking_time:
                min_booking_time = calculated_min_time
            
            # 営業終了時間を超えている場合は空のリストを返す
            if min_booking_time > business_hours.close_time:
                return JsonResponse({'available_times': []})
        
        # 既存の予約を取得
        existing_bookings = Booking.objects.filter(
            booking_date=booking_date,
            status__in=['pending', 'confirmed']
        )
        
        # 施術者が指定されている場合は、同じ施術者の予約のみチェック
        if therapist:
            existing_bookings = existing_bookings.filter(therapist=therapist)
        
        # 利用可能時間のリストを生成
        available_times = []
        current_time_slot = datetime.datetime.combine(booking_date, business_hours.open_time)
        end_time = datetime.datetime.combine(booking_date, business_hours.close_time)
        
        while current_time_slot + datetime.timedelta(minutes=service.duration_minutes) <= end_time:
            time_str = current_time_slot.strftime('%H:%M')
            slot_time = current_time_slot.time()
            
            # ①当日の場合は最小予約可能時間をチェック - 制限時間前の時間は完全に除外
            if is_today and slot_time < min_booking_time:
                current_time_slot += datetime.timedelta(minutes=interval_minutes)
                continue  # この時間スロットは完全にスキップ
            
            is_available = True
            
            # 既存予約・スケジュールとの重複チェック
            # 新しい予約の終了時間（インターバル込み）
            new_booking_start = current_time_slot
            new_booking_end = new_booking_start + datetime.timedelta(minutes=service.duration_minutes + buffer_minutes)
            
            # 既存の予約との重複チェック
            for existing_booking in existing_bookings:
                existing_start = datetime.datetime.combine(booking_date, existing_booking.booking_time)
                existing_end = existing_start + datetime.timedelta(
                    minutes=existing_booking.service.duration_minutes + buffer_minutes
                )
                
                # 時間の重複判定（インターバル時間も考慮）
                if (new_booking_start < existing_end and new_booking_end > existing_start):
                    is_available = False
                    break
            
            # スケジュール（予定）との重複チェック
            if is_available:
                try:
                    conflicting_schedules = Schedule.objects.filter(
                        schedule_date=booking_date,
                        is_active=True
                    )
                    
                    # 施術者が指定されている場合は、その施術者の予定のみチェック
                    if therapist:
                        conflicting_schedules = conflicting_schedules.filter(
                            Q(therapist=therapist) | Q(therapist__isnull=True)  # 全体予定も含む
                        )
                    
                    for schedule in conflicting_schedules:
                        schedule_start = datetime.datetime.combine(schedule.schedule_date, schedule.start_time)
                        schedule_end = datetime.datetime.combine(schedule.schedule_date, schedule.end_time)
                        
                        # 時間の重複判定
                        if (new_booking_start < schedule_end and new_booking_end > schedule_start):
                            is_available = False
                            break
                            
                except Exception as e:
                    logger.warning(f"スケジュールチェックエラー: {str(e)}")
            
            available_times.append({
                'time': time_str,
                'display': time_str,
                'available': is_available
            })
            
            current_time_slot += datetime.timedelta(minutes=interval_minutes)
        
        return JsonResponse({'available_times': available_times})
        
    except Exception as e:
        logger.error(f"利用可能時間取得エラー: {str(e)}")
        return JsonResponse({'error': 'サーバーエラーが発生しました'}, status=500)

# 予約管理機能（管理者用）
def cancel_booking(request, booking_id):
    """予約キャンセル"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        try:
            booking.status = 'cancelled'
            booking.save()
            
            # キャンセルメール送信
            try:
                send_booking_cancelled_email(booking)
                logger.info(f"予約キャンセル完了: {booking}")
            except Exception as e:
                logger.error(f"キャンセルメール送信エラー: {e}")
            
            messages.success(request, '予約をキャンセルしました。')
        except Exception as e:
            messages.error(request, 'キャンセル処理中にエラーが発生しました。')
            logger.error(f"予約キャンセルエラー: {str(e)}")
    
    return redirect('dashboard:booking_detail', booking_id=booking.id)

def confirm_booking(request, booking_id):
    """予約確定"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        try:
            booking.status = 'confirmed'
            booking.save()
            messages.success(request, '予約を確定しました。')
            logger.info(f"予約確定完了: {booking}")
        except Exception as e:
            messages.error(request, '確定処理中にエラーが発生しました。')
            logger.error(f"予約確定エラー: {str(e)}")
    
    return redirect('dashboard:booking_detail', booking_id=booking.id)

def complete_booking(request, booking_id):
    """予約完了"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        try:
            booking.status = 'completed'
            booking.save()
            messages.success(request, '施術を完了しました。')
            logger.info(f"予約完了: {booking}")
        except Exception as e:
            messages.error(request, '完了処理中にエラーが発生しました。')
            logger.error(f"予約完了エラー: {str(e)}")
    
    return redirect('dashboard:booking_detail', booking_id=booking.id)