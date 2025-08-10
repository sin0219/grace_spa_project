from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import BookingForm
from .models import Service

def booking_create(request):
    """予約作成ビュー"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save()
            
            # メール通知を送信
            try:
                send_booking_notification_emails(booking)
                if settings.BOOKING_REQUIRES_APPROVAL:
                    messages.success(
                        request, 
                        '予約申込みを受け付けました。管理者が確認後、確定のご連絡をいたします。確認メールをお送りしますので、ご確認ください。'
                    )
                else:
                    messages.success(
                        request, 
                        '予約が確定しました。確認メールをお送りしますので、ご確認ください。'
                    )
            except Exception as e:
                print(f"メール送信エラー: {e}")
                if settings.BOOKING_REQUIRES_APPROVAL:
                    messages.success(
                        request, 
                        '予約申込みを受け付けました。管理者が確認後、確定のご連絡をいたします。'
                    )
                else:
                    messages.success(request, '予約が確定しました。')
            
            return redirect('bookings:booking_success', booking_id=booking.id)
    else:
        form = BookingForm()
    
    # サービス一覧を取得
    services = Service.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'services': services,
        'title': '予約申込み - GRACE SPA'
    }
    return render(request, 'bookings/booking_form.html', context)

def booking_success(request, booking_id):
    """予約完了ページ"""
    from .models import Booking
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        messages.error(request, '予約情報が見つかりません。')
        return redirect('website:home')
    
    context = {
        'booking': booking,
        'title': '予約申込み完了 - GRACE SPA'
    }
    return render(request, 'bookings/booking_success.html', context)

def send_booking_notification_emails(booking):
    """予約通知メール送信"""
    # 顧客への通知メール
    send_customer_notification_email(booking)
    
    # 管理者への通知メール
    send_admin_notification_email(booking)

def send_customer_notification_email(booking):
    """顧客への予約通知メール"""
    if settings.BOOKING_REQUIRES_APPROVAL:
        subject = f'【GRACE SPA】予約申込み受付確認 - {booking.booking_date}'
        template_name = 'customer_booking_pending'
        status_text = '申込み受付'
        next_step = 'スタッフが確認後、確定のご連絡をいたします。'
    else:
        subject = f'【GRACE SPA】予約確定 - {booking.booking_date}'
        template_name = 'customer_booking_confirmed'
        status_text = '確定'
        next_step = '当日お会いできることを楽しみにしております。'
    
    message = f"""
{booking.customer.name} 様

この度は、GRACE SPAにご予約をいただき、ありがとうございます。
以下の内容で予約{status_text}いたしました。

■ 予約内容
予約番号: #{booking.id}
お客様名: {booking.customer.name}
サービス: {booking.service.name}
日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}
ステータス: {booking.get_status_display()}

■ お客様情報
メールアドレス: {booking.customer.email}
電話番号: {booking.customer.phone}
"""

    if booking.notes:
        message += f"""
ご要望・備考: {booking.notes}
"""

    message += f"""

■ 注意事項
・当店は完全予約制です
・ご予約時間の5分前にお越しください
・10分以上の遅刻をされた場合、足湯サービスができない場合があります
・当日キャンセル・無断キャンセルはキャンセル料が発生する場合があります

{next_step}

ご不明な点がございましたら、お気軽にお問い合わせください。

GRACE SPA
"""
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer.email],
        fail_silently=False,
    )

def send_admin_notification_email(booking):
    """管理者への予約通知メール"""
    subject = f'【GRACE SPA管理】新規予約申込み - {booking.booking_date} {booking.booking_time}'
    
    message = f"""
新しい予約申込みがありました。

■ 予約詳細
予約番号: #{booking.id}
申込日時: {booking.created_at.strftime('%Y年%m月%d日 %H:%M')}

■ 顧客情報
お名前: {booking.customer.name}
メールアドレス: {booking.customer.email}
電話番号: {booking.customer.phone}

■ 予約内容
サービス: {booking.service.name}
希望日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}
現在のステータス: {booking.get_status_display()}
"""

    if booking.notes:
        message += f"""
ご要望・備考: {booking.notes}
"""

    if settings.BOOKING_REQUIRES_APPROVAL:
        message += f"""

■ 対応が必要な作業
1. 顧客情報の確認
2. 予約枠の最終確認
3. 管理画面での予約承認: http://your-domain.com/dashboard/booking/{booking.id}/
4. 必要に応じて顧客への確認電話

管理画面: http://your-domain.com/dashboard/
"""
    else:
        message += f"""

■ 確認事項
管理画面で詳細を確認してください: http://your-domain.com/dashboard/booking/{booking.id}/
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
    )

def send_booking_confirmation_email(booking):
    """予約確定メール送信（管理者が承認時に使用）"""
    subject = f'【GRACE SPA】予約確定のお知らせ - {booking.booking_date}'
    
    message = f"""
{booking.customer.name} 様

お申込みいただいた予約が確定いたしました。

■ 確定した予約内容
予約番号: #{booking.id}
お客様名: {booking.customer.name}
サービス: {booking.service.name}
日時: {booking.booking_date} {booking.booking_time}
料金: ¥{booking.service.price:,}

■ 注意事項
・ご予約時間の5分前にお越しください
・10分以上の遅刻をされた場合、足湯サービスができない場合があります

当日お会いできることを楽しみにしております。

GRACE SPA
"""
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.customer.email],
        fail_silently=False,
    )