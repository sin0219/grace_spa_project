from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from bookings.models import Booking, Customer, Service
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
    
    # 統計情報
    stats = {
        'today_bookings': today_bookings.count(),
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
    
    context = {
        'title': '予約一覧 - GRACE SPA管理画面',
        'bookings': bookings,
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
                from bookings.views import send_booking_confirmation_email
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
    customers = customers.annotate(
        booking_count=Count('booking')
    ).order_by('-created_at')
    
    context = {
        'title': '顧客一覧 - GRACE SPA管理画面',
        'customers': customers,
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
    
    # 日付ごとに予約をグループ化
    bookings_by_date = {}
    for booking in bookings:
        date_str = booking.booking_date.strftime('%Y-%m-%d')
        if date_str not in bookings_by_date:
            bookings_by_date[date_str] = []
        bookings_by_date[date_str].append(booking)
    
    # カレンダーのデータを作成
    cal = calendar.monthcalendar(year, month)
    
    # カレンダーデータに予約情報を追加
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day': 0, 'bookings': []})
            else:
                day_date = datetime(year, month, day).date()
                day_str = day_date.strftime('%Y-%m-%d')
                day_bookings = bookings_by_date.get(day_str, [])
                is_today = day_date == timezone.now().date()
                
                week_data.append({
                    'day': day,
                    'date': day_date,
                    'date_str': day_str,
                    'bookings': day_bookings,
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
    
    # 日付ごとに予約をグループ化
    bookings_by_date = {}
    for booking in bookings:
        date_str = booking.booking_date.strftime('%Y-%m-%d')
        if date_str not in bookings_by_date:
            bookings_by_date[date_str] = []
        bookings_by_date[date_str].append(booking)
    
    # 週のデータを作成
    week_data = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_str = day_date.strftime('%Y-%m-%d')
        day_bookings = bookings_by_date.get(day_str, [])
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
        
        week_data.append({
            'date': day_date,
            'date_str': day_str,
            'bookings': day_bookings,
            'positioned_bookings': positioned_bookings,
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
    }
    return render(request, 'dashboard/week_calendar.html', context)