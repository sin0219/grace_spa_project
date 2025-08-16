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