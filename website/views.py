from django.shortcuts import render

def home(request):
    """ホームページのビュー"""
    context = {
        'title': 'GRACE SPA - プロフェッショナルオイルマッサージサロン',
        'services': [
            {'name': 'オイルマッサージ 90分', 'price': '9,000円', 'duration': '90分'},
            {'name': 'オイルマッサージ 120分', 'price': '11,500円', 'duration': '120分'},
            {'name': 'オイルマッサージ 150分', 'price': '14,500円', 'duration': '150分'},
        ]
    }
    return render(request, 'website/home.html', context)

def therapists(request):
    """施術者紹介ページのビュー"""
    from bookings.models import Therapist, BookingSettings
    
    # 予約設定を取得
    try:
        booking_settings = BookingSettings.get_current_settings()
        enable_therapist_selection = booking_settings.enable_therapist_selection
    except:
        enable_therapist_selection = True  # デフォルトは有効
    
    therapists = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'title': 'セラピスト紹介 - GRACE SPA',
        'therapists': therapists,
        'enable_therapist_selection': enable_therapist_selection  # 新規追加
    }
    return render(request, 'website/therapists.html', context)