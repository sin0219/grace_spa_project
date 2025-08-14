from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.template import Context, Template
from django.conf import settings
from django.utils import timezone
from django.utils.dateformat import DateFormat
import logging
from .models import EmailTemplate, EmailLog, MailSettings

logger = logging.getLogger(__name__)


def get_mail_settings():
    """メール設定を取得"""
    return MailSettings.get_settings()


def create_email_context(booking=None, customer=None, **extra_context):
    """メールテンプレート用のコンテキストを作成"""
    mail_settings = get_mail_settings()
    
    context = {
        'mail_settings': mail_settings,
        'site_name': 'GRACE SPA',
        'site_url': getattr(settings, 'SITE_URL', 'https://gracespa.com'),
        'current_year': timezone.now().year,
        **extra_context
    }
    
    if booking:
        # 時間フォーマット（timeformatの代わりに手動でフォーマット）
        booking_time_str = booking.booking_time.strftime('%H:%M')
        booking_date_str = DateFormat(booking.booking_date).format('Y年n月j日(l)')
        
        context.update({
            'booking': booking,
            'customer': booking.customer,
            'service': booking.service,
            'therapist': booking.therapist,
            'booking_date_formatted': booking_date_str,
            'booking_time_formatted': booking_time_str,
            'booking_datetime_formatted': f"{booking_date_str} {booking_time_str}",
        })
    
    if customer:
        context.update({
            'customer': customer,
        })
    
    return context


def render_email_template(template_type, context_data=None):
    """メールテンプレートをレンダリング"""
    try:
        template = EmailTemplate.objects.get(template_type=template_type, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.error(f"メールテンプレートが見つかりません: {template_type}")
        return None, None, None
    
    if context_data is None:
        context_data = {}
    
    # コンテキストを作成
    context = create_email_context(**context_data)
    
    # 件名をレンダリング
    subject_template = Template(template.subject)
    subject = subject_template.render(Context(context))
    
    # 本文（テキスト）をレンダリング
    body_text_template = Template(template.body_text)
    body_text = body_text_template.render(Context(context))
    
    # 本文（HTML）をレンダリング
    body_html = None
    if template.body_html:
        body_html_template = Template(template.body_html)
        body_html = body_html_template.render(Context(context))
    
    return subject, body_text, body_html


def send_email_async(recipient_email, subject, body_text, body_html=None, 
                    template=None, booking=None, scheduled_at=None):
    """非同期でメールを送信するためのログエントリを作成"""
    
    # 受信者名を取得
    recipient_name = ''
    if booking and booking.customer:
        recipient_name = booking.customer.name
    
    # EmailLogエントリを作成
    email_log = EmailLog.objects.create(
        template=template,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_text=body_text,
        body_html=body_html or '',
        booking=booking,
        scheduled_at=scheduled_at or timezone.now(),
        status='pending'
    )
    
    return email_log


def send_email_now(email_log):
    """メールログからメールを即座に送信"""
    mail_settings = get_mail_settings()
    
    try:
        # 送信者情報
        from_email = f"{mail_settings.from_name} <{mail_settings.from_email}>"
        
        # EmailMultiAlternativesを使用してテキストとHTMLメールを送信
        email = EmailMultiAlternatives(
            subject=email_log.subject,
            body=email_log.body_text,
            from_email=from_email,
            to=[email_log.recipient_email],
            reply_to=[mail_settings.reply_to_email] if mail_settings.reply_to_email else None
        )
        
        # HTMLバージョンがある場合は添付
        if email_log.body_html:
            email.attach_alternative(email_log.body_html, "text/html")
        
        # メール送信
        email.send()
        
        # ログを更新
        email_log.status = 'sent'
        email_log.sent_at = timezone.now()
        email_log.error_message = ''
        email_log.save()
        
        logger.info(f"メール送信成功: {email_log.recipient_email}")
        return True
        
    except Exception as e:
        # エラー処理
        email_log.status = 'failed'
        email_log.error_message = str(e)
        email_log.save()
        
        logger.error(f"メール送信失敗: {email_log.recipient_email} - {str(e)}")
        return False


def send_booking_confirmation_email(booking):
    """予約確認メールを送信"""
    mail_settings = get_mail_settings()
    
    if not mail_settings.enable_customer_notifications:
        return False
    
    context_data = {'booking': booking}
    subject, body_text, body_html = render_email_template('booking_confirmation_customer', context_data)
    
    if not subject:
        return False
    
    template = EmailTemplate.objects.filter(template_type='booking_confirmation_customer', is_active=True).first()
    email_log = send_email_async(
        recipient_email=booking.customer.email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        template=template,
        booking=booking
    )
    
    # 即座に送信
    return send_email_now(email_log)


def send_admin_new_booking_email(booking):
    """管理者向け新規予約通知メールを送信"""
    mail_settings = get_mail_settings()
    
    if not mail_settings.enable_admin_notifications:
        return False
    
    context_data = {'booking': booking}
    subject, body_text, body_html = render_email_template('booking_confirmation_admin', context_data)
    
    if not subject:
        return False
    
    template = EmailTemplate.objects.filter(template_type='booking_confirmation_admin', is_active=True).first()
    email_log = send_email_async(
        recipient_email=mail_settings.admin_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        template=template,
        booking=booking
    )
    
    # 即座に送信
    return send_email_now(email_log)


def send_booking_reminder_email(booking, hours_before):
    """予約リマインダーメールを送信"""
    mail_settings = get_mail_settings()
    
    if not mail_settings.enable_reminder_emails:
        return False
    
    context_data = {
        'booking': booking,
        'hours_before': hours_before
    }
    subject, body_text, body_html = render_email_template('booking_reminder', context_data)
    
    if not subject:
        return False
    
    template = EmailTemplate.objects.filter(template_type='booking_reminder', is_active=True).first()
    email_log = send_email_async(
        recipient_email=booking.customer.email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        template=template,
        booking=booking
    )
    
    # 即座に送信
    return send_email_now(email_log)


def send_booking_cancelled_email(booking, cancelled_by_customer=True):
    """予約キャンセル通知メールを送信"""
    mail_settings = get_mail_settings()
    
    # 顧客向けキャンセル通知
    if mail_settings.enable_customer_notifications:
        context_data = {
            'booking': booking,
            'cancelled_by_customer': cancelled_by_customer
        }
        subject, body_text, body_html = render_email_template('booking_cancelled_customer', context_data)
        
        if subject:
            template = EmailTemplate.objects.filter(template_type='booking_cancelled_customer', is_active=True).first()
            email_log = send_email_async(
                recipient_email=booking.customer.email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                template=template,
                booking=booking
            )
            send_email_now(email_log)
    
    # 管理者向けキャンセル通知
    if mail_settings.enable_admin_notifications:
        context_data = {
            'booking': booking,
            'cancelled_by_customer': cancelled_by_customer
        }
        subject, body_text, body_html = render_email_template('booking_cancelled_admin', context_data)
        
        if subject:
            template = EmailTemplate.objects.filter(template_type='booking_cancelled_admin', is_active=True).first()
            email_log = send_email_async(
                recipient_email=mail_settings.admin_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                template=template,
                booking=booking
            )
            send_email_now(email_log)


def send_booking_status_changed_email(booking, old_status, new_status):
    """予約ステータス変更通知メールを送信"""
    mail_settings = get_mail_settings()
    
    if not mail_settings.enable_customer_notifications:
        return False
    
    context_data = {
        'booking': booking,
        'old_status': old_status,
        'new_status': new_status
    }
    subject, body_text, body_html = render_email_template('booking_status_changed', context_data)
    
    if not subject:
        return False
    
    template = EmailTemplate.objects.filter(template_type='booking_status_changed', is_active=True).first()
    email_log = send_email_async(
        recipient_email=booking.customer.email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        template=template,
        booking=booking
    )
    
    # 即座に送信
    return send_email_now(email_log)


def send_test_email(recipient_email):
    """テストメール送信"""
    mail_settings = get_mail_settings()
    
    subject = "[テスト] GRACE SPA メール設定テスト"
    body_text = f"""このメールはGRACE SPAのメール設定テストです。

送信日時: {timezone.now().strftime('%Y年%m月%d日 %H:%M:%S')}
送信者: {mail_settings.from_name} <{mail_settings.from_email}>

このメールが正常に受信できていれば、メール設定は正しく動作しています。

{mail_settings.signature}"""
    
    try:
        from_email = f"{mail_settings.from_name} <{mail_settings.from_email}>"
        
        send_mail(
            subject=subject,
            message=body_text,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=False
        )
        
        logger.info(f"テストメール送信成功: {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"テストメール送信失敗: {recipient_email} - {str(e)}")
        return False


def process_scheduled_emails():
    """スケジュールされたメールを処理（Celeryタスクまたはcronで実行）"""
    from django.utils import timezone
    
    # 送信予定時刻を過ぎた未送信メールを取得
    pending_emails = EmailLog.objects.filter(
        status__in=['pending', 'retry'],
        scheduled_at__lte=timezone.now()
    ).order_by('scheduled_at')
    
    success_count = 0
    failed_count = 0
    
    for email_log in pending_emails:
        if send_email_now(email_log):
            success_count += 1
        else:
            failed_count += 1
            
            # 最大再送信回数をチェック
            if email_log.retry_count >= 3:
                email_log.status = 'failed'
                email_log.save()
    
    logger.info(f"スケジュールメール処理完了 - 成功: {success_count}, 失敗: {failed_count}")
    return success_count, failed_count


def schedule_reminder_emails():
    """リマインダーメールをスケジュール"""
    from bookings.models import Booking
    from datetime import datetime, timedelta
    
    mail_settings = get_mail_settings()
    if not mail_settings.enable_reminder_emails:
        return
    
    reminder_hours = mail_settings.get_reminder_hours_list()
    now = timezone.now()
    
    for hours_before in reminder_hours:
        # リマインダー送信対象の予約を取得
        target_datetime = now + timedelta(hours=hours_before)
        target_date = target_datetime.date()
        target_time_start = (target_datetime - timedelta(minutes=30)).time()
        target_time_end = (target_datetime + timedelta(minutes=30)).time()
        
        bookings = Booking.objects.filter(
            booking_date=target_date,
            booking_time__range=(target_time_start, target_time_end),
            status__in=['confirmed', 'pending']
        )
        
        for booking in bookings:
            # 既にリマインダーが送信されているかチェック
            existing_reminder = EmailLog.objects.filter(
                booking=booking,
                template__template_type='booking_reminder',
                status='sent'
            ).exists()
            
            if not existing_reminder:
                context_data = {
                    'booking': booking,
                    'hours_before': hours_before
                }
                subject, body_text, body_html = render_email_template('booking_reminder', context_data)
                
                if subject:
                    template = EmailTemplate.objects.filter(template_type='booking_reminder', is_active=True).first()
                    send_email_async(
                        recipient_email=booking.customer.email,
                        subject=subject,
                        body_text=body_text,
                        body_html=body_html,
                        template=template,
                        booking=booking,
                        scheduled_at=now
                    )