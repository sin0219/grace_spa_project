from django.shortcuts import render

def home(request):
    """ホームページのビュー"""
    context = {
        'title': 'GRACE SPA - プロフェッショナルオイルマッサージサロン',
        'services': [
            {
                'name': 'オイルリンパマッサージ',
                'duration': '90分～',
                'price': '9,000円～',
                'description': '凝りをほぐすハワイ式ロミロミを取り組んだオイルリンパマッサージ'
            },
            {
                'name': '高炭酸オイルリンパマッサージ',
                'duration': '130分～',
                'price': '14,000円～',
                'description': '高濃度二酸化炭素配合オイルを用いることで血行促進を促し、筋肉疲労・むくみ・冷えを改善します。'
            },
            {
                'name': 'オイルリンパマッサージ＋タイ古式マッサージ',
                'duration': '190分～',
                'price': '18,500円～',
                'description': '熟練のタイ古式マッサージを併せることで辛い凝り・疲労を解消',
                'is_combo': True
            },
            {
                'name': 'ヘッドスパ',
                'duration': '20分～',
                'price': '2,500円～',
                'description': '※ヘッドスパはオプションメニューのため、他のメニューと組み合わせてご利用ください。'
            }
        ]
    }
    return render(request, 'website/home.html', context)

# website/views.py の home_en 関数を以下に置き換えてください

def home_en(request):
    """英語版ホームページのビュー"""
    from bookings.models import Service
    
    # データベースからサービス情報を取得して英語化
    services_data = Service.objects.filter(is_active=True).order_by('sort_order', 'name')
    services = []
    
    for service in services_data:
        # 英語名・説明を取得（なければ日本語をフォールバック）
        service_name_en = service.get_name('en')
        service_desc_en = service.get_description('en')
        
        # コンボメニュー判定（日本語名ベースで判定）
        is_combo = 'タイ古式' in service.name or 'コンボ' in service.name
        
        services.append({
            'name': service_name_en,
            'duration': f'{service.duration_minutes} min~',
            'price': f'¥{service.price:,}~',
            'description': service_desc_en,
            'is_combo': is_combo
        })
    
    # フォールバック：データベースにサービスがない場合のデフォルト英語版サービス
    if not services:
        services = [
            {
                'name': 'Oil Lymphatic Massage',
                'duration': '90 min~',
                'price': '¥9,000~',
                'description': 'Oil lymphatic massage incorporating Hawaiian Lomi Lomi techniques to relieve tension and stiffness',
                'is_combo': False
            },
            {
                'name': 'High Carbonated Oil Lymphatic Massage',
                'duration': '130 min~',
                'price': '¥14,000~',
                'description': 'Using high-concentration CO2-infused oil to promote blood circulation and improve muscle fatigue, swelling, and coldness',
                'is_combo': False
            },
            {
                'name': 'Oil Lymphatic + Thai Traditional Massage',
                'duration': '190 min~',
                'price': '¥18,500~',
                'description': 'Combination of skilled Thai traditional massage to relieve stubborn tension and fatigue',
                'is_combo': True
            },
            {
                'name': 'Head Spa',
                'duration': '20 min~',
                'price': '¥2,500~',
                'description': '* Head spa is an add-on service. Please combine with other treatments.',
                'is_combo': False
            }
        ]
    
    context = {
        'title': 'GRACE SPA - Professional Oil Massage Salon',
        'services': services
    }
    return render(request, 'en/website/home_en.html', context)

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
        'enable_therapist_selection': enable_therapist_selection
    }
    return render(request, 'website/therapists.html', context)

# website/views.py の therapists_en 関数を以下に置き換えてください

def therapists_en(request):
    """英語版施術者紹介ページのビュー"""
    from bookings.models import Therapist, BookingSettings
    
    # 予約設定を取得
    try:
        booking_settings = BookingSettings.get_current_settings()
        enable_therapist_selection = booking_settings.enable_therapist_selection
    except:
        enable_therapist_selection = True  # デフォルトは有効
    
    # セラピスト情報を取得して英語版に変換
    therapists_data = Therapist.objects.filter(is_active=True).order_by('sort_order', 'name')
    therapists = []
    
    for therapist in therapists_data:
        therapist_info = {
            'id': therapist.id,
            'name': therapist.name,
            'display_name_en': therapist.get_display_name('en'),
            'description_en': therapist.get_description('en'),
            'image': therapist.image,
            'is_active': therapist.is_active,
            'sort_order': therapist.sort_order,
            'is_featured': getattr(therapist, 'is_featured', False)  # is_featuredフィールドがあれば使用
        }
        therapists.append(therapist_info)
    
    context = {
        'title': 'Our Therapists - GRACE SPA',
        'therapists': therapists,
        'enable_therapist_selection': enable_therapist_selection
    }
    return render(request, 'en/website/therapists_en.html', context)