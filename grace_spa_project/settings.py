import os
from pathlib import Path

# .envファイルを読み込むための設定
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenvがインストールされていない場合は環境変数から直接読み込み
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

LOCAL_APPS = [
    'website',
    'bookings',
    'dashboard',
    'emails',  # メール機能アプリ
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'bookings.middleware.MaintenanceModeMiddleware',
    'bookings.middleware.BookingSecurityMiddleware',
    'bookings.middleware.SecurityHeadersMiddleware',
    'bookings.middleware.SuspiciousActivityMiddleware',
]

ROOT_URLCONF = 'grace_spa_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'grace_spa_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===========================================
# メール設定（環境変数から取得）
# ===========================================

# 本番環境用（Gmail SMTP）
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-app-password')

# 開発環境用（コンソール出力）- デバッグ時に使用
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 送信者情報
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# 管理者メールアドレス
ADMINS = [
    ('GRACE SPA 管理者', EMAIL_HOST_USER),
]

# メール設定
EMAIL_SUBJECT_PREFIX = '[GRACE SPA] '
EMAIL_TIMEOUT = 30

# 予約関連メール設定
BOOKING_NOTIFICATION_EMAILS = {
    'CUSTOMER_BOOKING_CONFIRMATION': True,  # 顧客への予約確認メール
    'CUSTOMER_BOOKING_REMINDER': True,      # 顧客への予約リマインダー
    'ADMIN_NEW_BOOKING': True,              # 管理者への新規予約通知
    'ADMIN_BOOKING_CANCELLED': True,        # 管理者への予約キャンセル通知
}

# リマインダーメール送信タイミング（時間前）
BOOKING_REMINDER_HOURS = [24, 2]  # 24時間前と2時間前

# その他のメール関連設定
EMAIL_USE_LOCALTIME = True

# サイト設定
SITE_URL = os.environ.get('SITE_URL', 'https://gracespa.com')

# 予約設定
BOOKING_REQUIRES_APPROVAL = os.environ.get('BOOKING_REQUIRES_APPROVAL', 'True').lower() == 'true'