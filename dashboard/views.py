from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from bookings.models import Booking, Customer, Service, Schedule, BusinessHours, Therapist, BookingSettings, MaintenanceMode
from datetime import datetime, timedelta
import calendar

@staff_member_required
def dashboard_home(request):
    """ダッシュボードホーム"""
    today = timezone.now().date()
    
    # 今日の予約
    today_bookings = Booking.objects.filter(
        booking_date=today,
        status__in=['pending', 'confirmed']
    ).order_by('booking_time')
    
    # 今日の予定
    try:
        today_schedules = Schedule.objects.filter(
            schedule_date=today,
            is_active=True
        ).order_by('start_time')
    except:
        today_schedules = []
    
    # 統計情報
    stats = {
        'today_bookings': today_bookings.count(),
        'today_schedules': len(today_schedules),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'total_customers': Customer.objects.count(),
        'this_month_bookings': Booking.objects.filter(
            booking_date__year=today.year,
            booking_date__month=today.month
        ).count(),
    }
    
    # 最近の予約（今後1週間）
    upcoming_bookings = Booking.objects.filter(
        booking_date__gte=today,
        booking_date__lte=today + timedelta(days=7),
        status__in=['pending', 'confirmed']
    ).order_by('booking_date', 'booking_time')[:10]
    
    context = {
        'title': 'ダッシュボード - GRACE SPA管理画面',
        'today': today,
        'today_bookings': today_bookings,
        'today_schedules': today_schedules,
        'upcoming_bookings': upcoming_bookings,
        'stats': stats,
    }
    return render(request, 'dashboard/home.html', context)

@staff_member_required
def booking_list(request):
    """予約一覧"""
    # フィルター処理
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    bookings = Booking.objects.all()
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            bookings = bookings.filter(booking_date=filter_date)
        except ValueError:
            pass
    
    bookings = bookings.order_by('-booking_date', '-booking_time')
    
    booking_stats = {
        'total_bookings': bookings.count(),
        'male_bookings': bookings.filter(customer__gender='male').count(),
        'female_bookings': bookings.filter(customer__gender='female').count(),
        'first_visit_bookings': bookings.filter(customer__is_first_visit=True).count(),
        'pending_bookings': bookings.filter(status='pending').count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
        'completed_bookings': bookings.filter(status='completed').count(),
        'cancelled_bookings': bookings.filter(status='cancelled').count(),
    }
    
    context = {
        'title': '予約一覧 - GRACE SPA管理画面',
        'bookings': bookings,
        'booking_stats': booking_stats,  # ★ 統計データを追加
        'status_choices': Booking.STATUS_CHOICES,
        'current_status': status_filter,
        'current_date': date_filter,
    }
    return render(request, 'dashboard/booking_list.html', context)

@staff_member_required
def booking_detail(request, booking_id):
    """予約詳細"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            booking.status = 'confirmed'
            booking.save()
            
            # 予約確定メールを送信
            try:
                from emails.utils import send_booking_confirmation_email
                send_booking_confirmation_email(booking)
                messages.success(request, f'{booking.customer.name}様の予約を確定し、確定メールを送信しました。')
            except Exception as e:
                print(f"確定メール送信エラー: {e}")
                messages.success(request, f'{booking.customer.name}様の予約を確定しました。')
        
        elif action == 'complete':
            booking.status = 'completed'
            booking.save()
            messages.success(request, f'{booking.customer.name}様の施術を完了にしました。')
        
        elif action == 'cancel':
            booking.status = 'cancelled'
            booking.save()
            messages.warning(request, f'{booking.customer.name}様の予約をキャンセルしました。')
        
        return redirect('dashboard:booking_detail', booking_id=booking.id)
    
    context = {
        'title': f'予約詳細 - {booking.customer.name}様',
        'booking': booking,
    }
    return render(request, 'dashboard/booking_detail.html', context)

@staff_member_required
def customer_list(request):
    """顧客一覧"""
    search = request.GET.get('search', '')
    
    customers = Customer.objects.all()
    
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # 予約回数を追加
    customers = customers.order_by('-created_at')
    
    # ★ 新規追加: 顧客統計の計算
    customer_stats = {
        'total_customers': customers.count(),
        'male_customers': customers.filter(gender='male').count(),
        'female_customers': customers.filter(gender='female').count(),
        'unset_gender_customers': customers.filter(Q(gender__isnull=True) | Q(gender='')).count(),
        'first_visit_customers': customers.filter(is_first_visit=True).count(),
        'repeat_customers': customers.filter(is_first_visit=False).count(),
    }
    
    # 予約回数別の統計（リピーター（2回以上）、常連客（5回以上）を計算）
    # 注意：booking_count はプロパティなので、直接フィルターできない
    # ここではPythonでカウントする
    repeat_customers_count = 0
    vip_customers_count = 0
    
    for customer in customers:
        booking_count = customer.booking_count
        if booking_count >= 2:
            repeat_customers_count += 1
        if booking_count >= 5:
            vip_customers_count += 1
    
    customer_stats['repeat_customers_with_bookings'] = repeat_customers_count
    customer_stats['vip_customers'] = vip_customers_count

    context = {
        'title': '顧客一覧 - GRACE SPA管理画面',
        'customers': customers,
        'customer_stats': customer_stats,  # ★ 統計データを追加
        'search_query': search,
    }
    return render(request, 'dashboard/customer_list.html', context)

@staff_member_required
def calendar_view(request):
    """カレンダー表示"""
    # 現在の年月を取得
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # 月の最初と最後の日を取得
    first_day = datetime(year, month, 1).date()
    if month == 12:
        last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # その月の予約を取得
    bookings = Booking.objects.filter(
        booking_date__gte=first_day,
        booking_date__lte=last_day,
        status__in=['pending', 'confirmed']
    ).order_by('booking_date', 'booking_time')
    
    # その月の予定を取得
    try:
        schedules = Schedule.objects.filter(
            schedule_date__gte=first_day,
            schedule_date__lte=last_day,
            is_active=True
        ).order_by('schedule_date', 'start_time')
    except:
        schedules = []
    
    # 日付ごとに予約をグループ化
    bookings_by_date = {}
    for booking in bookings:
        date_str = booking.booking_date.strftime('%Y-%m-%d')
        if date_str not in bookings_by_date:
            bookings_by_date[date_str] = []
        bookings_by_date[date_str].append(booking)
    
    # 日付ごとに予定をグループ化
    schedules_by_date = {}
    for schedule in schedules:
        date_str = schedule.schedule_date.strftime('%Y-%m-%d')
        if date_str not in schedules_by_date:
            schedules_by_date[date_str] = []
        schedules_by_date[date_str].append(schedule)
    
    # カレンダーのデータを作成
    cal = calendar.monthcalendar(year, month)
    
    # カレンダーデータに予約・予定情報を追加
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day': 0, 'bookings': [], 'schedules': []})
            else:
                day_date = datetime(year, month, day).date()
                day_str = day_date.strftime('%Y-%m-%d')
                day_bookings = bookings_by_date.get(day_str, [])
                day_schedules = schedules_by_date.get(day_str, [])
                is_today = day_date == timezone.now().date()
                
                week_data.append({
                    'day': day,
                    'date': day_date,
                    'date_str': day_str,
                    'bookings': day_bookings,
                    'schedules': day_schedules,
                    'is_today': is_today
                })
        calendar_data.append(week_data)
    
    # 前月・次月の計算
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    context = {
        'title': f'{year}年{month}月 カレンダー - GRACE SPA管理画面',
        'calendar_data': calendar_data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'bookings_by_date': bookings_by_date,
        'schedules_by_date': schedules_by_date,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'today': timezone.now().date(),
    }
    return render(request, 'dashboard/calendar.html', context)

@staff_member_required
def week_view(request):
    """週単位カレンダー表示"""
    # 現在の日付から週を取得
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    day = int(request.GET.get('day', today.day))
    
    try:
        current_date = datetime(year, month, day).date()
    except ValueError:
        current_date = today
    
    # その週の月曜日を計算
    days_since_monday = current_date.weekday()
    week_start = current_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    # 前週・次週の計算
    prev_week_start = week_start - timedelta(days=7)
    next_week_start = week_start + timedelta(days=7)
    
    # その週の予約を取得
    bookings = Booking.objects.filter(
        booking_date__gte=week_start,
        booking_date__lte=week_end,
        status__in=['pending', 'confirmed', 'completed']
    ).order_by('booking_date', 'booking_time')
    
    # その週の予定を取得
    try:
        schedules = Schedule.objects.filter(
            schedule_date__gte=week_start,
            schedule_date__lte=week_end,
            is_active=True
        ).order_by('schedule_date', 'start_time')
    except:
        schedules = []
    
    # 日付ごとに予約をグループ化
    bookings_by_date = {}
    for booking in bookings:
        date_str = booking.booking_date.strftime('%Y-%m-%d')
        if date_str not in bookings_by_date:
            bookings_by_date[date_str] = []
        bookings_by_date[date_str].append(booking)
    
    # 日付ごとに予定をグループ化
    schedules_by_date = {}
    for schedule in schedules:
        date_str = schedule.schedule_date.strftime('%Y-%m-%d')
        if date_str not in schedules_by_date:
            schedules_by_date[date_str] = []
        schedules_by_date[date_str].append(schedule)
    
    # 週のデータを作成
    week_data = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_str = day_date.strftime('%Y-%m-%d')
        day_bookings = bookings_by_date.get(day_str, [])
        day_schedules = schedules_by_date.get(day_str, [])
        is_today = day_date == timezone.now().date()
        
        # 予約の位置を計算
        positioned_bookings = []
        for booking in day_bookings:
            hour = booking.booking_time.hour
            minute = booking.booking_time.minute
            # 9:00を基準(0px)として位置を計算
            top_position = (hour - 9) * 60 + minute
            if top_position < 0:
                top_position = 0
            
            positioned_bookings.append({
                'booking': booking,
                'top_position': top_position
            })
        
        # 予定の位置を計算
        positioned_schedules = []
        for schedule in day_schedules:
            hour = schedule.start_time.hour
            minute = schedule.start_time.minute
            top_position = (hour - 9) * 60 + minute
            if top_position < 0:
                top_position = 0
            
            # 予定の高さを計算
            try:
                duration = schedule.duration_minutes
                height = duration  # 1分 = 1px
            except:
                height = 60  # デフォルト60分
            
            positioned_schedules.append({
                'schedule': schedule,
                'top_position': top_position,
                'height': height
            })
        
        week_data.append({
            'date': day_date,
            'date_str': day_str,
            'bookings': day_bookings,
            'schedules': day_schedules,
            'positioned_bookings': positioned_bookings,
            'positioned_schedules': positioned_schedules,
            'is_today': is_today,
            'day_name': ['月', '火', '水', '木', '金', '土', '日'][i]
        })
    
    context = {
        'title': f'{week_start.strftime("%Y年%m月%d日")} 週 - GRACE SPA管理画面',
        'week_data': week_data,
        'week_start': week_start,
        'week_end': week_end,
        'current_date': current_date,
        'prev_week': prev_week_start,
        'next_week': next_week_start,
        'today': timezone.now().date(),
        'bookings_by_date': bookings_by_date,
        'schedules_by_date': schedules_by_date,
    }
    return render(request, 'dashboard/week_calendar.html', context)

# ===== 新規追加: 予約・予定管理機能 =====

@staff_member_required
def booking_create_dashboard(request):
    """ダッシュボードから予約登録"""
    # dashboard/forms.py が未作成の場合はシンプルなメッセージを表示
    try:
        from .forms import DashboardBookingForm
        
        if request.method == 'POST':
            form = DashboardBookingForm(request.POST)
            if form.is_valid():
                booking = form.save()
                messages.success(request, f'{booking.customer.name}様の予約を登録しました。')
                return redirect('dashboard:booking_detail', booking_id=booking.id)
        else:
            form = DashboardBookingForm()
        
        context = {
            'title': '新規予約登録 - GRACE SPA管理画面',
            'form': form,
        }
        return render(request, 'dashboard/booking_create.html', context)
        
    except ImportError:
        messages.error(request, 'dashboard/forms.py が作成されていません。管理画面から予約登録を行ってください。')
        return redirect('dashboard:booking_list')

@staff_member_required
def schedule_list(request):
    """予定一覧"""
    try:
        date_filter = request.GET.get('date', '')
        type_filter = request.GET.get('type', '')
        
        schedules = Schedule.objects.filter(is_active=True)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                schedules = schedules.filter(schedule_date=filter_date)
            except ValueError:
                pass
        
        if type_filter:
            schedules = schedules.filter(schedule_type=type_filter)
        
        schedules = schedules.order_by('-schedule_date', 'start_time')
        
        context = {
            'title': '予定一覧 - GRACE SPA管理画面',
            'schedules': schedules,
            'type_choices': Schedule.SCHEDULE_TYPE_CHOICES,
            'current_date': date_filter,
            'current_type': type_filter,
        }
        return render(request, 'dashboard/schedule_list.html', context)
        
    except:
        messages.error(request, 'Scheduleモデルがマイグレーションされていません。まずマイグレーションを実行してください。')
        return redirect('dashboard:home')

@staff_member_required
def schedule_create(request):
    """予定登録"""
    try:
        from .forms import ScheduleForm
        
        if request.method == 'POST':
            form = ScheduleForm(request.POST)
            if form.is_valid():
                schedule = form.save(commit=False)
                schedule.created_by = request.user.username
                schedule.save()
                messages.success(request, f'予定「{schedule.title}」を登録しました。')
                return redirect('dashboard:schedule_list')
        else:
            form = ScheduleForm()
        
        context = {
            'title': '新規予定登録 - GRACE SPA管理画面',
            'form': form,
        }
        return render(request, 'dashboard/schedule_create.html', context)
        
    except ImportError:
        messages.error(request, 'dashboard/forms.py が作成されていません。')
        return redirect('dashboard:schedule_list')

@staff_member_required
def schedule_detail(request, schedule_id):
    """予定詳細・編集"""
    try:
        from .forms import ScheduleForm
        
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        if request.method == 'POST':
            form = ScheduleForm(request.POST, instance=schedule)
            if form.is_valid():
                form.save()
                messages.success(request, f'予定「{schedule.title}」を更新しました。')
                return redirect('dashboard:schedule_list')
        else:
            form = ScheduleForm(instance=schedule)
        
        # この予定と重複する予約があるかチェック
        try:
            conflicting_bookings = schedule.conflicts_with_bookings()
        except:
            conflicting_bookings = []
        
        context = {
            'title': f'予定詳細 - {schedule.title}',
            'schedule': schedule,
            'form': form,
            'conflicting_bookings': conflicting_bookings,
        }
        return render(request, 'dashboard/schedule_detail.html', context)
        
    except ImportError:
        messages.error(request, 'dashboard/forms.py が作成されていません。')
        return redirect('dashboard:schedule_list')

@staff_member_required
def schedule_list(request):
    """予定一覧"""
    try:
        date_filter = request.GET.get('date', '')
        type_filter = request.GET.get('type', '')
        
        schedules = Schedule.objects.filter(is_active=True)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                schedules = schedules.filter(schedule_date=filter_date)
            except ValueError:
                pass
        
        if type_filter:
            schedules = schedules.filter(schedule_type=type_filter)
        
        schedules = schedules.order_by('-schedule_date', 'start_time')
        
        # Schedule.SCHEDULE_TYPE_CHOICESを安全に取得
        try:
            type_choices = Schedule.SCHEDULE_TYPE_CHOICES
        except AttributeError:
            type_choices = []
        
        context = {
            'title': '予定一覧 - GRACE SPA管理画面',
            'schedules': schedules,
            'type_choices': type_choices,
            'current_date': date_filter,
            'current_type': type_filter,
        }
        return render(request, 'dashboard/schedule_list.html', context)
        
    except Exception as e:
        # 具体的なエラー情報を表示
        import traceback
        error_details = traceback.format_exc()
        print(f"Schedule List Error: {str(e)}")
        print(f"Traceback: {error_details}")
        
        messages.error(request, f'予定一覧の表示中にエラーが発生しました: {str(e)}')
        return redirect('dashboard:home')
# ===== API エンドポイント =====

@staff_member_required
def get_available_times_api(request):
    """管理者用：利用可能時間取得API（①当日時刻チェック ②直前予約制限対応）"""
    date_str = request.GET.get('date')
    therapist_id = request.GET.get('therapist_id')
    service_id = request.GET.get('service_id')
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
    
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # 現在時刻を取得
    now = timezone.now()
    current_date = now.date()
    current_time = now.time()
    
    # 営業時間を取得
    weekday = booking_date.weekday()
    try:
        business_hour = BusinessHours.objects.get(weekday=weekday)
        if not business_hour.is_open:
            return JsonResponse({'time_slots': []})
    except BusinessHours.DoesNotExist:
        # デフォルト営業時間を作成
        business_hour_data = {
            'is_open': True,
            'open_time': datetime.strptime('09:00', '%H:%M').time(),
            'close_time': datetime.strptime('20:00', '%H:%M').time(),
            'last_booking_time': datetime.strptime('19:00', '%H:%M').time(),
        }
        
        class BusinessHourDefault:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        business_hour = BusinessHourDefault(business_hour_data)
    
    # 予約設定を取得
    try:
        settings_obj = BookingSettings.get_current_settings()
        buffer_minutes = settings_obj.treatment_buffer_minutes
        # ②直前予約制限の設定を取得
        min_advance_minutes = getattr(settings_obj, 'min_advance_minutes', 20)  # デフォルト20分
    except:
        buffer_minutes = 15  # デフォルト15分インターバル
        min_advance_minutes = 20  # デフォルト20分前まで
    
    # ①当日の場合の最小予約可能時間を計算
    min_booking_time = business_hour.open_time
    if booking_date == current_date:
        # 現在時刻 + 直前予約制限時間
        min_datetime = now + timedelta(minutes=min_advance_minutes)
        calculated_min_time = min_datetime.time()
        
        # 営業開始時間と比較して遅い方を採用
        if calculated_min_time > min_booking_time:
            min_booking_time = calculated_min_time
        
        # 営業終了時間を超えている場合は空の時間スロットを返す
        if min_booking_time > business_hour.last_booking_time:
            return JsonResponse({'time_slots': []})
    
    # 既存予約を取得
    existing_bookings = Booking.objects.filter(
        booking_date=booking_date,
        status__in=['pending', 'confirmed']
    )
    
    if therapist_id:
        existing_bookings = existing_bookings.filter(therapist_id=therapist_id)
    else:
        existing_bookings = existing_bookings.filter(therapist__isnull=True)
    
    # 既存予定を取得
    try:
        existing_schedules = Schedule.objects.filter(
            schedule_date=booking_date,
            is_active=True
        )
        
        if therapist_id:
            existing_schedules = existing_schedules.filter(
                Q(therapist_id=therapist_id) | Q(therapist__isnull=True)
            )
    except:
        existing_schedules = []
    
    # 時間スロットを10分刻みで生成
    time_slots = []
    current_time_slot = datetime.combine(booking_date, business_hour.open_time)
    end_time = datetime.combine(booking_date, business_hour.last_booking_time)
    
    while current_time_slot <= end_time:
        time_str = current_time_slot.strftime('%H:%M')
        slot_time = current_time_slot.time()
        status = 'available'
        conflict_info = ''
        
        # ①当日の場合は最小予約可能時間をチェック
        if booking_date == current_date and slot_time < min_booking_time:
            status = 'past_time'
            if slot_time < current_time:
                conflict_info = '過去の時間です'
            else:
                conflict_info = f'{min_advance_minutes}分前までの予約は受付できません'
        else:
            # 予約との重複チェック（正しいサービス時間とインターバルを使用）
            for booking in existing_bookings:
                booking_start = datetime.combine(booking_date, booking.booking_time)
                # 実際のサービス時間とインターバルを使用
                service_duration = booking.service.duration_minutes
                booking_end = booking_start + timedelta(minutes=service_duration + buffer_minutes)
                
                if booking_start <= current_time_slot < booking_end:
                    status = 'booking_conflict'
                    conflict_info = f'{booking.customer.name} - {booking.service.name} ({service_duration}分+{buffer_minutes}分)'
                    break
            
            # 予定との重複チェック
            if status == 'available':
                for schedule in existing_schedules:
                    schedule_start = datetime.combine(booking_date, schedule.start_time)
                    schedule_end = datetime.combine(booking_date, schedule.end_time)
                    
                    if schedule_start <= current_time_slot < schedule_end:
                        status = 'schedule_conflict'
                        conflict_info = f'{schedule.title}'
                        break
        
        time_slots.append({
            'time': time_str,
            'status': status,
            'conflict_info': conflict_info
        })
        
        current_time_slot += timedelta(minutes=10)  # 10分刻み
    
    return JsonResponse({'time_slots': time_slots})

@staff_member_required
def get_schedule_times_api(request):
    """予定作成用：時間スロット取得API（①当日時刻チェック ②直前予約制限対応）"""
    date_str = request.GET.get('date')
    therapist_id = request.GET.get('therapist_id')
    start_time_str = request.GET.get('start_time')
    
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # 現在時刻を取得
    now = timezone.now()
    current_date = now.date()
    current_time = now.time()
    
    # ✅ 追加: 営業時間を取得
    weekday = target_date.weekday()
    try:
        business_hour = BusinessHours.objects.get(weekday=weekday)
        if not business_hour.is_open:
            return JsonResponse({'time_slots': []})
    except BusinessHours.DoesNotExist:
        # デフォルト営業時間を作成
        business_hour_data = {
            'is_open': True,
            'open_time': datetime.strptime('09:00', '%H:%M').time(),
            'close_time': datetime.strptime('20:00', '%H:%M').time(),
            'last_booking_time': datetime.strptime('19:00', '%H:%M').time(),
        }
        
        class BusinessHourDefault:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        business_hour = BusinessHourDefault(business_hour_data)
   
    # 予約設定を取得
    try:
        settings_obj = BookingSettings.get_current_settings()
        buffer_minutes = settings_obj.treatment_buffer_minutes
        # ②直前予約制限の設定を取得（予定作成では制限を緩くする）
        min_advance_minutes = getattr(settings_obj, 'min_advance_minutes', 20)
        # 予定作成の場合は制限を半分にする（10分前まで）
        min_advance_minutes = min_advance_minutes // 2
    except:
        buffer_minutes = 15  # デフォルト15分インターバル
        min_advance_minutes = 10  # デフォルト10分前まで
    
    # ①当日の場合の最小予定作成可能時間を計算
    min_schedule_time = business_hour.open_time
    if target_date == current_date:
        # 現在時刻 + 直前制限時間
        min_datetime = now + timedelta(minutes=min_advance_minutes)
        calculated_min_time = min_datetime.time()
        
        # 6:00と比較して遅い方を採用
        if calculated_min_time > min_schedule_time:
            min_schedule_time = calculated_min_time
    
    # 既存予約を取得
    existing_bookings = Booking.objects.filter(
        booking_date=target_date,
        status__in=['pending', 'confirmed']
    )
    
    if therapist_id:
        existing_bookings = existing_bookings.filter(therapist_id=therapist_id)
    
    # 既存予定を取得
    try:
        existing_schedules = Schedule.objects.filter(
            schedule_date=target_date,
            is_active=True
        )
        
        if therapist_id:
            existing_schedules = existing_schedules.filter(therapist_id=therapist_id)
    except:
        existing_schedules = []
    
    # 時間スロットを10分刻みで生成（6:00-22:00）
    time_slots = []

    
    # 開始時間の範囲を営業時間に限定
    if start_time_str:
        # 終了時間の選択肢を生成（開始時間より後）
        start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
        
        # 開始時間より後で営業時間内の時間を生成
        current_time_slot = datetime.combine(target_date, start_time_obj) + timedelta(minutes=10)
        end_boundary = datetime.combine(target_date, business_hour.close_time)
    else:
        # 開始時間の選択肢を生成
        current_time_slot = datetime.combine(target_date, min_schedule_time)
        end_boundary = datetime.combine(target_date, business_hour.last_booking_time)
    
    while current_time_slot <= end_boundary:
            time_str = current_time_slot.strftime('%H:%M')
            slot_time = current_time_slot.time()
            status = 'available'
            conflict_info = ''
            
            # ①当日の場合は最小予定作成可能時間をチェック
            if target_date == current_date and slot_time < min_schedule_time:
                status = 'past_time'
                if slot_time < current_time:
                    conflict_info = '過去の時間です'
                else:
                    conflict_info = f'{min_advance_minutes}分前までの予定作成は制限されています'
            else:
                # 予約との重複チェック（正しいサービス時間とインターバルを使用）
                for booking in existing_bookings:
                    booking_start = datetime.combine(target_date, booking.booking_time)
                    # 実際のサービス時間とインターバルを使用
                    service_duration = booking.service.duration_minutes
                    booking_end = booking_start + timedelta(minutes=service_duration + buffer_minutes)
                    
                    if booking_start <= current_time_slot < booking_end:
                        status = 'booking_conflict'
                        conflict_info = f'{booking.customer.name} - {booking.service.name} ({service_duration}分+{buffer_minutes}分)'
                        break
                
                # 予定との重複チェック
                if status == 'available':
                    for schedule in existing_schedules:
                        schedule_start = datetime.combine(target_date, schedule.start_time)
                        schedule_end = datetime.combine(target_date, schedule.end_time)
                        
                        if schedule_start <= current_time_slot < schedule_end:
                            status = 'schedule_conflict'
                            conflict_info = f'{schedule.title}'
                            break
            
            time_slots.append({
                'time': time_str,
                'status': status,
                'conflict_info': conflict_info
            })
            current_time_slot += timedelta(minutes=10)  # 10分刻み
    return JsonResponse({'time_slots': time_slots})
# 既存のdashboard/views.pyの最後に以下の関数を追加してください

@staff_member_required
def maintenance_settings(request):
    """メンテナンス設定管理"""
    maintenance = MaintenanceMode.get_current_settings()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'enable':
            # メンテナンスモードを有効にする
            maintenance.is_enabled = True
            maintenance.start_time = timezone.now()
            maintenance.end_time = None
            maintenance.save()
            messages.success(request, 'メンテナンスモードを有効にしました。予約フォームは一時停止されています。')
            
        elif action == 'disable':
            # メンテナンスモードを無効にする
            maintenance.is_enabled = False
            maintenance.end_time = timezone.now()
            maintenance.save()
            messages.success(request, 'メンテナンスモードを無効にしました。予約フォームが再開されました。')
            
        elif action == 'update_message':
            # メッセージと連絡先を更新
            maintenance.message = request.POST.get('message', maintenance.message)
            maintenance.contact_email = request.POST.get('contact_email', maintenance.contact_email)
            maintenance.contact_phone = request.POST.get('contact_phone', maintenance.contact_phone)
            maintenance.save()
            messages.success(request, 'メンテナンス設定を更新しました。')
        
        return redirect('dashboard:maintenance_settings')
    
    context = {
        'title': 'メンテナンス設定 - GRACE SPA管理画面',
        'maintenance': maintenance,
    }
    return render(request, 'dashboard/maintenance_settings.html', context)

@staff_member_required
def toggle_maintenance(request):
    """AJAX用：メンテナンスモードの切り替え"""
    if request.method == 'POST':
        try:
            maintenance = MaintenanceMode.get_current_settings()
            
            # 現在の状態を反転
            maintenance.is_enabled = not maintenance.is_enabled
            
            if maintenance.is_enabled:
                maintenance.start_time = timezone.now()
                maintenance.end_time = None
                status_message = 'メンテナンスモードを有効にしました'
            else:
                maintenance.end_time = timezone.now()
                status_message = 'メンテナンスモードを無効にしました'
            
            maintenance.save()
            
            return JsonResponse({
                'success': True,
                'is_enabled': maintenance.is_enabled,
                'message': status_message,
                'start_time': maintenance.start_time.strftime('%Y-%m-%d %H:%M') if maintenance.start_time else None,
                'end_time': maintenance.end_time.strftime('%Y-%m-%d %H:%M') if maintenance.end_time else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'エラーが発生しました: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '無効なリクエストです'})
# dashboard/views.py の既存コードの最後に以下の関数を追加してください

@staff_member_required
def sales_dashboard(request):
    """売上ダッシュボード"""
    from django.db.models import Sum, Count, Avg
    from datetime import datetime, timedelta
    import calendar
    
    today = timezone.now().date()
    
    # ★ 新機能: URL パラメータから年月を取得
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # 選択された年月の月初日を計算
    try:
        selected_month = datetime(year, month, 1).date()
    except ValueError:
        # 無効な年月の場合は現在月を使用
        selected_month = today.replace(day=1)
        year = today.year
        month = today.month
    
    current_month = selected_month
    
    # 📊 月別売上（過去12ヶ月）
    monthly_sales = []
    for i in range(12):
        if i == 0:
            month_start = current_month
        else:
            # 前月を計算
            if current_month.month - i <= 0:
                year = current_month.year - 1
                month = 12 + (current_month.month - i)
            else:
                year = current_month.year
                month = current_month.month - i
            month_start = current_month.replace(year=year, month=month, day=1)
        
        # 翌月の1日を計算
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1, day=1)
        
        month_revenue = Booking.objects.filter(
            booking_date__gte=month_start,
            booking_date__lt=next_month,
            status='completed'
        ).aggregate(
            total=Sum('service__price'),
            count=Count('id'),
            avg_price=Avg('service__price')
        )
        
        monthly_sales.append({
            'month': month_start.strftime('%Y年%m月'),
            'month_short': month_start.strftime('%m月'),
            'revenue': month_revenue['total'] or 0,
            'bookings': month_revenue['count'] or 0,
            'avg_price': round(month_revenue['avg_price'] or 0, 0),
        })
    
    # 新しい順にソート（最新月が最後に）
    monthly_sales.reverse()
    
    # 📈 選択月の日別売上
    daily_sales = []
    days_in_selected_month = calendar.monthrange(year, month)[1]
    
    for day in range(1, days_in_selected_month + 1):
        target_date = selected_month.replace(day=day)
        
        daily_revenue = Booking.objects.filter(
            booking_date=target_date,
            status='completed'
        ).aggregate(
            total=Sum('service__price'),
            count=Count('id')
        )
        
        daily_sales.append({
            'date': target_date.strftime('%m/%d'),
            'day': day,
            'revenue': daily_revenue['total'] or 0,
            'bookings': daily_revenue['count'] or 0,
            'is_today': target_date == today,
            'is_future': target_date > today
        })
    
    # 🛍️ サービス別売上（選択月）
    next_month = current_month.replace(month=current_month.month + 1, day=1) if current_month.month < 12 else current_month.replace(year=current_month.year + 1, month=1, day=1)
    
    service_sales = Booking.objects.filter(
        booking_date__gte=current_month,
        booking_date__lt=next_month,
        status='completed'
    ).values('service__name', 'service__price').annotate(
        count=Count('id'),
        total=Sum('service__price')
    ).order_by('-total')
    
    # 💆‍♀️ セラピスト別売上（選択月）
    therapist_sales = Booking.objects.filter(
        booking_date__gte=current_month,
        booking_date__lt=next_month,
        status='completed',
        therapist__isnull=False
    ).values('therapist__display_name').annotate(
        count=Count('id'),
        total=Sum('service__price')
    ).order_by('-total')
    
    # 📊 選択月の統計サマリー
    current_month_bookings = Booking.objects.filter(
        booking_date__gte=current_month,
        booking_date__lt=next_month,
        status='completed'
    )
    
    current_month_stats = current_month_bookings.aggregate(
        total_revenue=Sum('service__price'),
        total_bookings=Count('id'),
        avg_price=Avg('service__price')
    )
    
    # 前月との比較（選択月の前月）
    last_month = current_month.replace(month=current_month.month - 1) if current_month.month > 1 else current_month.replace(year=current_month.year - 1, month=12)
    last_month_end = current_month
    
    last_month_stats = Booking.objects.filter(
        booking_date__gte=last_month,
        booking_date__lt=last_month_end,
        status='completed'
    ).aggregate(
        total_revenue=Sum('service__price'),
        total_bookings=Count('id')
    )
    
    # 成長率計算
    revenue_growth = 0
    booking_growth = 0
    
    if last_month_stats['total_revenue'] and current_month_stats['total_revenue']:
        revenue_growth = ((current_month_stats['total_revenue'] - last_month_stats['total_revenue']) / last_month_stats['total_revenue']) * 100
    
    if last_month_stats['total_bookings'] and current_month_stats['total_bookings']:
        booking_growth = ((current_month_stats['total_bookings'] - last_month_stats['total_bookings']) / last_month_stats['total_bookings']) * 100
    
    # 📋 統計サマリー
    summary_stats = {
        'total_revenue': current_month_stats['total_revenue'] or 0,
        'total_bookings': current_month_stats['total_bookings'] or 0,
        'avg_price': round(current_month_stats['avg_price'] or 0, 0),
        'revenue_growth': round(revenue_growth, 1),
        'booking_growth': round(booking_growth, 1),
        'avg_daily_revenue': round((current_month_stats['total_revenue'] or 0) / selected_month.day if selected_month <= today else (current_month_stats['total_revenue'] or 0) / days_in_selected_month, 0),
        'last_month_revenue': last_month_stats['total_revenue'] or 0,
        'last_month_bookings': last_month_stats['total_bookings'] or 0,
    }
    
    # ★ 新機能: 月選択用のデータを生成
    # 最初の予約から現在まで、または過去24ヶ月のどちらか短い方
    first_booking = Booking.objects.order_by('booking_date').first()
    if first_booking:
        start_year = first_booking.booking_date.year
        start_month = first_booking.booking_date.month
    else:
        # 予約がない場合は過去12ヶ月から
        start_year = today.year - 1
        start_month = today.month
    
    # 月選択肢のリストを生成
    available_months = []
    current_date = datetime(start_year, start_month, 1).date()
    end_date = today.replace(day=1)
    
    while current_date <= end_date:
        available_months.append({
            'year': current_date.year,
            'month': current_date.month,
            'display': current_date.strftime('%Y年%m月'),
            'is_selected': current_date.year == year and current_date.month == month
        })
        
        # 次の月を計算
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # 降順にソート（新しい月が最初に）
    available_months.reverse()
    
    context = {
        'title': '売上ダッシュボード - GRACE SPA管理画面',
        'monthly_sales': monthly_sales,
        'daily_sales': daily_sales,
        'service_sales': service_sales,
        'therapist_sales': therapist_sales,
        'summary_stats': summary_stats,
        'current_month': current_month.strftime('%Y年%m月'),
        'last_month': last_month.strftime('%Y年%m月'),
        'selected_year': year,
        'selected_month': month,
        'available_months': available_months,  # ★ 新機能: 月選択用データ
        'is_current_month': selected_month.year == today.year and selected_month.month == today.month,  # ★ 現在月かどうか
    }
    return render(request, 'dashboard/sales_dashboard.html', context)

@staff_member_required
def schedule_delete(request, schedule_id):
    """予定削除（直接実行）"""
    try:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        if request.method == 'POST':
            # POSTリクエストで直接削除実行
            title = schedule.title
            schedule.delete()
            messages.success(request, f'予定「{title}」を削除しました。')
            return redirect('dashboard:schedule_list')
        else:
            # GETリクエストの場合はエラー（安全のため）
            messages.error(request, '無効なリクエストです。')
            return redirect('dashboard:schedule_list')
        
    except Schedule.DoesNotExist:
        messages.error(request, '予定が見つかりません。')
        return redirect('dashboard:schedule_list')
    except Exception as e:
        messages.error(request, f'削除中にエラーが発生しました: {str(e)}')
        return redirect('dashboard:schedule_list')