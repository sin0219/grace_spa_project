from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
import json

class BookingSecurityMiddleware:
    """予約セキュリティ用ミドルウェア"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 予約フォームへのアクセス制限
        if request.path == '/booking/' and request.method == 'POST':
            if not self.check_rate_limit(request):
                return HttpResponse(
                    "申し訳ございません。短時間での予約申込みが多すぎます。しばらく時間をおいてからお試しください。",
                    status=429
                )
        
        response = self.get_response(request)
        return response
    
    def check_rate_limit(self, request):
        """IP制限チェック"""
        ip_address = self.get_client_ip(request)
        
        # IP単位の制限（1時間に3回まで）
        ip_key = f"booking_rate_limit_ip_{ip_address}"
        ip_attempts = cache.get(ip_key, 0)
        
        hourly_limit = getattr(settings, 'BOOKING_HOURLY_LIMIT_PER_IP', 3)
        
        if ip_attempts >= hourly_limit:
            return False
        
        # カウントを増加
        cache.set(ip_key, ip_attempts + 1, 3600)  # 1時間
        
        return True
    
    def get_client_ip(self, request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SecurityHeadersMiddleware:
    """セキュリティヘッダー追加ミドルウェア"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # セキュリティヘッダーを追加
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response

class SuspiciousActivityMiddleware:
    """不審なアクティビティ検出ミドルウェア"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 不審なパターンを検出（APIリクエストは除外）
        if self.detect_suspicious_activity(request):
            self.log_suspicious_activity(request)
        
        response = self.get_response(request)
        return response
    
    def detect_suspicious_activity(self, request):
        """不審なアクティビティを検出"""
        # APIリクエストは除外
        if request.path.startswith('/booking/api/'):
            return False
        
        # 管理画面のAPIリクエストも除外
        if request.path.startswith('/dashboard/api/'):
            return False
        
        # AJAXリクエストは除外
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return False
        
        ip_address = self.get_client_ip(request)
        
        # 短時間での大量アクセス検出（フォーム送信のみ）
        if request.path.startswith('/booking/') and request.method == 'POST':
            access_key = f"booking_access_{ip_address}"
            current_time = timezone.now().timestamp()
            
            # 過去5分間のアクセス履歴を取得
            access_history = cache.get(access_key, [])
            
            # 古いアクセス履歴を削除（5分以内のみ保持）
            access_history = [
                timestamp for timestamp in access_history 
                if current_time - timestamp < 300  # 5分
            ]
            
            # 新しいアクセスを追加
            access_history.append(current_time)
            cache.set(access_key, access_history, 300)
            
            # 5分間に5回以上のフォーム送信は不審とみなす
            if len(access_history) > 5:
                return True
        
        return False
    
    def log_suspicious_activity(self, request):
        """不審なアクティビティをログに記録"""
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'path': request.path,
            'method': request.method,
        }
        
        print(f"🚨 不審なアクティビティ検出: {json.dumps(log_data, ensure_ascii=False)}")
        
        # 実際のプロダクションでは、より本格的なログシステムに記録
        # logger.warning(f"Suspicious activity detected: {log_data}")
    
    def get_client_ip(self, request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# bookings/middleware.py に以下のクラスを追加

class MaintenanceModeMiddleware:
    """メンテナンスモードチェックミドルウェア"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 管理画面やダッシュボードのアクセスは許可
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/dashboard/') or
            request.path.startswith('/static/') or
            request.path.startswith('/media/')):
            return self.get_response(request)
        
        # メンテナンスモードの確認
        try:
            from .models import MaintenanceMode
            maintenance = MaintenanceMode.get_current_settings()
            
            if maintenance.is_enabled:
                # 予約関連のページのみにアクセスした場合（ホームとセラピスト紹介は除外）
                if (request.path.startswith('/booking/') or
                    request.path.startswith('/bookings/')):  # トップページとセラピスト紹介は閲覧可能
                    
                    # メンテナンス画面を表示
                    from django.shortcuts import render
                    from django.http import HttpResponse
                    
                    context = {
                        'maintenance': maintenance,
                        'title': 'メンテナンス中 - GRACE SPA'
                    }
                    
                    response = render(request, 'maintenance.html', context)
                    response.status_code = 503  # Service Unavailable
                    return response
                    
        except Exception:
            # メンテナンスモードの確認でエラーが発生した場合は通常処理を継続
            pass
        
        return self.get_response(request)