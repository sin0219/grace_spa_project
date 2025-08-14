from django.core.management.base import BaseCommand
from emails.models import EmailTemplate


class Command(BaseCommand):
    help = 'デフォルトのメールテンプレートを作成します'
    
    def handle(self, *args, **options):
        # 顧客向け予約確認メール（テキスト版）
        customer_confirmation_text = """{{ customer.name }} 様

この度は、GRACE SPAをご利用いただき、誠にありがとうございます。
ご予約を承りましたので、詳細をご確認ください。

【ご予約詳細】
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }} ({{ service.duration_minutes }}分)
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}
料金: {{ service.price }}円

{% if booking.notes %}
【ご要望・備考】
{{ booking.notes }}
{% endif %}

【ご来店について】
・ご予約時間の5分前にお越しください
・お着替えをご用意しております
・貴重品はロッカーにお預けください

【注意事項】
・ご予約の変更・キャンセルは前日までにご連絡ください
・当日キャンセルの場合、キャンセル料が発生する場合があります

ご不明な点がございましたら、お気軽にお問い合わせください。
お客様のご来店を心よりお待ちしております。

{{ mail_settings.signature }}"""

        # 顧客向け予約確認メール（HTML版）
        customer_confirmation_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #8b7355; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f5f0; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { background: #333; color: white; padding: 15px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GRACE SPA</h1>
            <p>ご予約確認</p>
        </div>
        <div class="content">
            <p>{{ customer.name }} 様</p>
            <p>この度は、GRACE SPAをご利用いただき、誠にありがとうございます。<br>
            ご予約を承りましたので、詳細をご確認ください。</p>
            
            <div class="booking-details">
                <h3>ご予約詳細</h3>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }} ({{ service.duration_minutes }}分)</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
                <p><strong>料金:</strong> {{ service.price }}円</p>
                {% if booking.notes %}
                <p><strong>ご要望・備考:</strong><br>{{ booking.notes|linebreaks }}</p>
                {% endif %}
            </div>
            
            <h3>ご来店について</h3>
            <ul>
                <li>ご予約時間の5分前にお越しください</li>
                <li>お着替えをご用意しております</li>
                <li>貴重品はロッカーにお預けください</li>
            </ul>
            
            <h3>注意事項</h3>
            <ul>
                <li>ご予約の変更・キャンセルは前日までにご連絡ください</li>
                <li>当日キャンセルの場合、キャンセル料が発生する場合があります</li>
            </ul>
        </div>
        <div class="footer">
            <p>ご不明な点がございましたら、お気軽にお問い合わせください。<br>
            お客様のご来店を心よりお待ちしております。</p>
            <pre>{{ mail_settings.signature }}</pre>
        </div>
    </div>
</body>
</html>"""

        # 管理者向け新規予約通知（テキスト版）
        admin_notification_text = """新規予約が入りました。

【予約詳細】
顧客名: {{ customer.name }}
メール: {{ customer.email }}
電話: {{ customer.phone }}
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }} ({{ service.duration_minutes }}分)
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}
料金: {{ service.price }}円
ステータス: {{ booking.get_status_display }}

{% if booking.notes %}
【ご要望・備考】
{{ booking.notes }}
{% endif %}

管理画面で確認・承認を行ってください。"""

        # 管理者向け新規予約通知（HTML版）
        admin_notification_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>新規予約通知</h1>
        </div>
        <div class="content">
            <p>新規予約が入りました。</p>
            
            <div class="booking-details">
                <h3>予約詳細</h3>
                <p><strong>顧客名:</strong> {{ customer.name }}</p>
                <p><strong>メール:</strong> {{ customer.email }}</p>
                <p><strong>電話:</strong> {{ customer.phone }}</p>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }} ({{ service.duration_minutes }}分)</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
                <p><strong>料金:</strong> {{ service.price }}円</p>
                <p><strong>ステータス:</strong> {{ booking.get_status_display }}</p>
                {% if booking.notes %}
                <p><strong>ご要望・備考:</strong><br>{{ booking.notes|linebreaks }}</p>
                {% endif %}
            </div>
            
            <p>管理画面で確認・承認を行ってください。</p>
        </div>
    </div>
</body>
</html>"""

        # 予約リマインダー（テキスト版）
        reminder_text = """{{ customer.name }} 様

いつもGRACE SPAをご利用いただき、ありがとうございます。

明日のご予約についてリマインダーをお送りいたします。

【ご予約詳細】
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }} ({{ service.duration_minutes }}分)
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}

【お願い】
・ご予約時間の5分前にお越しください
・ご都合が悪くなりましたら、お早めにご連絡ください

お客様のご来店を心よりお待ちしております。

{{ mail_settings.signature }}"""

        # 予約リマインダー（HTML版）
        reminder_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GRACE SPA</h1>
            <p>ご予約リマインダー</p>
        </div>
        <div class="content">
            <p>{{ customer.name }} 様</p>
            <p>いつもGRACE SPAをご利用いただき、ありがとうございます。</p>
            <p>ご予約についてリマインダーをお送りいたします。</p>
            
            <div class="booking-details">
                <h3>ご予約詳細</h3>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }} ({{ service.duration_minutes }}分)</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
            </div>
            
            <h3>お願い</h3>
            <ul>
                <li>ご予約時間の5分前にお越しください</li>
                <li>ご都合が悪くなりましたら、お早めにご連絡ください</li>
            </ul>
            
            <p>お客様のご来店を心よりお待ちしております。</p>
        </div>
        <div class="footer">
            <pre>{{ mail_settings.signature }}</pre>
        </div>
    </div>
</body>
</html>"""

        # 顧客向けキャンセル通知（テキスト版）
        cancel_customer_text = """{{ customer.name }} 様

{% if cancelled_by_customer %}
ご予約のキャンセルを承りました。
{% else %}
誠に申し訳ございませんが、こちらの都合により下記ご予約をキャンセルさせていただきます。
{% endif %}

【キャンセルされた予約】
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }}
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}

{% if not cancelled_by_customer %}
ご迷惑をおかけして誠に申し訳ございません。
改めてご予約をお取りいただけますと幸いです。
{% endif %}

ご不明な点がございましたら、お気軽にお問い合わせください。

{{ mail_settings.signature }}"""

        # 顧客向けキャンセル通知（HTML版）
        cancel_customer_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GRACE SPA</h1>
            <p>ご予約キャンセル</p>
        </div>
        <div class="content">
            <p>{{ customer.name }} 様</p>
            {% if cancelled_by_customer %}
            <p>ご予約のキャンセルを承りました。</p>
            {% else %}
            <p>誠に申し訳ございませんが、こちらの都合により下記ご予約をキャンセルさせていただきます。</p>
            {% endif %}
            
            <div class="booking-details">
                <h3>キャンセルされた予約</h3>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }}</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
            </div>
            
            {% if not cancelled_by_customer %}
            <p>ご迷惑をおかけして誠に申し訳ございません。<br>
            改めてご予約をお取りいただけますと幸いです。</p>
            {% endif %}
            
            <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>
        </div>
        <div class="footer">
            <pre>{{ mail_settings.signature }}</pre>
        </div>
    </div>
</body>
</html>"""

        # 管理者向けキャンセル通知（テキスト版）
        cancel_admin_text = """予約がキャンセルされました。

【キャンセルされた予約】
顧客名: {{ customer.name }}
メール: {{ customer.email }}
電話: {{ customer.phone }}
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }}
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}

{% if cancelled_by_customer %}
※ 顧客によるキャンセル
{% else %}
※ 店舗側によるキャンセル
{% endif %}"""

        # 管理者向けキャンセル通知（HTML版）
        cancel_admin_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>予約キャンセル通知</h1>
        </div>
        <div class="content">
            <p>予約がキャンセルされました。</p>
            
            <div class="booking-details">
                <h3>キャンセルされた予約</h3>
                <p><strong>顧客名:</strong> {{ customer.name }}</p>
                <p><strong>メール:</strong> {{ customer.email }}</p>
                <p><strong>電話:</strong> {{ customer.phone }}</p>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }}</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
            </div>
            
            {% if cancelled_by_customer %}
            <p><strong>※ 顧客によるキャンセル</strong></p>
            {% else %}
            <p><strong>※ 店舗側によるキャンセル</strong></p>
            {% endif %}
        </div>
    </div>
</body>
</html>"""

        # 予約ステータス変更通知（テキスト版）
        status_change_text = """{{ customer.name }} 様

ご予約の状況が変更されましたのでお知らせいたします。

【予約詳細】
日時: {{ booking_datetime_formatted }}
サービス: {{ service.name }}
施術者: {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}
状況: {{ new_status }} (以前: {{ old_status }})

{% if new_status == "confirmed" %}
ご予約が確定いたしました。
ご来店を心よりお待ちしております。
{% elif new_status == "completed" %}
ご利用ありがとうございました。
またのご来店をお待ちしております。
{% endif %}

ご不明な点がございましたら、お気軽にお問い合わせください。

{{ mail_settings.signature }}"""

        # 予約ステータス変更通知（HTML版）
        status_change_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .status { font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GRACE SPA</h1>
            <p>ご予約状況変更</p>
        </div>
        <div class="content">
            <p>{{ customer.name }} 様</p>
            <p>ご予約の状況が変更されましたのでお知らせいたします。</p>
            
            <div class="booking-details">
                <h3>予約詳細</h3>
                <p><strong>日時:</strong> {{ booking_datetime_formatted }}</p>
                <p><strong>サービス:</strong> {{ service.name }}</p>
                <p><strong>施術者:</strong> {% if therapist %}{{ therapist.display_name }}{% else %}指名なし{% endif %}</p>
                <p><strong>状況:</strong> <span class="status">{{ new_status }}</span> (以前: {{ old_status }})</p>
            </div>
            
            {% if new_status == "confirmed" %}
            <p>ご予約が確定いたしました。<br>
            ご来店を心よりお待ちしております。</p>
            {% elif new_status == "completed" %}
            <p>ご利用ありがとうございました。<br>
            またのご来店をお待ちしております。</p>
            {% endif %}
            
            <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>
        </div>
        <div class="footer">
            <pre>{{ mail_settings.signature }}</pre>
        </div>
    </div>
</body>
</html>"""

        # テンプレートデータの定義
        templates = [
            {
                'name': '顧客向け予約確認メール',
                'template_type': 'booking_confirmation_customer',
                'subject': '[GRACE SPA] ご予約を承りました - {{ booking_datetime_formatted }}',
                'body_text': customer_confirmation_text,
                'body_html': customer_confirmation_html
            },
            {
                'name': '管理者向け新規予約通知',
                'template_type': 'booking_confirmation_admin',
                'subject': '[GRACE SPA] 新規予約 - {{ customer.name }}様 {{ booking_datetime_formatted }}',
                'body_text': admin_notification_text,
                'body_html': admin_notification_html
            },
            {
                'name': '予約リマインダー',
                'template_type': 'booking_reminder',
                'subject': '[GRACE SPA] ご予約のリマインダー - {{ booking_datetime_formatted }}',
                'body_text': reminder_text,
                'body_html': reminder_html
            },
            {
                'name': '顧客向けキャンセル通知',
                'template_type': 'booking_cancelled_customer',
                'subject': '[GRACE SPA] ご予約のキャンセルについて',
                'body_text': cancel_customer_text,
                'body_html': cancel_customer_html
            },
            {
                'name': '管理者向けキャンセル通知',
                'template_type': 'booking_cancelled_admin',
                'subject': '[GRACE SPA] 予約キャンセル - {{ customer.name }}様',
                'body_text': cancel_admin_text,
                'body_html': cancel_admin_html
            },
            {
                'name': '予約ステータス変更通知',
                'template_type': 'booking_status_changed',
                'subject': '[GRACE SPA] ご予約状況の変更について',
                'body_text': status_change_text,
                'body_html': status_change_html
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'作成: {template.name}')
                )
            else:
                # 既存テンプレートを更新
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'更新: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'テンプレート初期化完了: 作成 {created_count}件, 更新 {updated_count}件'
            )
        )