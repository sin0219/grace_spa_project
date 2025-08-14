# Generated migration file
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='テンプレート名')),
                ('template_type', models.CharField(choices=[('booking_confirmation_customer', '顧客向け予約確認'), ('booking_confirmation_admin', '管理者向け新規予約通知'), ('booking_reminder', '予約リマインダー'), ('booking_cancelled_customer', '顧客向けキャンセル通知'), ('booking_cancelled_admin', '管理者向けキャンセル通知'), ('booking_status_changed', '予約ステータス変更通知')], max_length=50, unique=True, verbose_name='テンプレート種別')),
                ('subject', models.CharField(max_length=200, verbose_name='件名')),
                ('body_text', models.TextField(verbose_name='本文（テキスト）')),
                ('body_html', models.TextField(blank=True, verbose_name='本文（HTML）')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': 'メールテンプレート',
                'verbose_name_plural': 'メールテンプレート',
                'ordering': ['template_type'],
            },
        ),
        migrations.CreateModel(
            name='MailSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_email', models.EmailField(default='noreply@gracespa.com', max_length=254, verbose_name='送信者メールアドレス')),
                ('from_name', models.CharField(default='GRACE SPA', max_length=100, verbose_name='送信者名')),
                ('reply_to_email', models.EmailField(blank=True, max_length=254, verbose_name='返信先メールアドレス')),
                ('admin_email', models.EmailField(max_length=254, verbose_name='管理者メールアドレス')),
                ('admin_name', models.CharField(default='管理者', max_length=100, verbose_name='管理者名')),
                ('enable_customer_notifications', models.BooleanField(default=True, verbose_name='顧客への通知メールを有効にする')),
                ('enable_admin_notifications', models.BooleanField(default=True, verbose_name='管理者への通知メールを有効にする')),
                ('enable_reminder_emails', models.BooleanField(default=True, verbose_name='リマインダーメールを有効にする')),
                ('reminder_hours_before', models.CharField(default='24,2', help_text='カンマ区切りで複数指定可能（例：24,2 = 24時間前と2時間前）', max_length=50, verbose_name='リマインダー送信時間（時間前）')),
                ('signature', models.TextField(default='\n――――――――――――――――――\nGRACE SPA\n〒000-0000 住所をここに記入\nTEL: 000-0000-0000\nEMAIL: info@gracespa.com\nWEB: https://gracespa.com\n――――――――――――――――――\n', verbose_name='メール署名')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': 'メール設定',
                'verbose_name_plural': 'メール設定',
            },
        ),
        migrations.CreateModel(
            name='EmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_email', models.EmailField(max_length=254, verbose_name='送信先メールアドレス')),
                ('recipient_name', models.CharField(blank=True, max_length=100, verbose_name='送信先名前')),
                ('subject', models.CharField(max_length=200, verbose_name='件名')),
                ('body_text', models.TextField(verbose_name='本文（テキスト）')),
                ('body_html', models.TextField(blank=True, verbose_name='本文（HTML）')),
                ('status', models.CharField(choices=[('pending', '送信待ち'), ('sent', '送信完了'), ('failed', '送信失敗'), ('retry', '再送信待ち')], default='pending', max_length=20, verbose_name='送信状況')),
                ('error_message', models.TextField(blank=True, verbose_name='エラーメッセージ')),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='送信予定日時')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='送信日時')),
                ('retry_count', models.IntegerField(default=0, verbose_name='再送信回数')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bookings.booking', verbose_name='関連予約')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='emails.emailtemplate', verbose_name='テンプレート')),
            ],
            options={
                'verbose_name': 'メール送信ログ',
                'verbose_name_plural': 'メール送信ログ',
                'ordering': ['-created_at'],
            },
        ),
    ]