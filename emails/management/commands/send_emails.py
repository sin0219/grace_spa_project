from django.core.management.base import BaseCommand
from django.utils import timezone
from emails.utils import process_scheduled_emails


class Command(BaseCommand):
    help = 'スケジュールされたメールを送信します'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には送信せず、送信対象のメールのみ表示',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('=== DRY RUN MODE ===')
            from emails.models import EmailLog
            pending_emails = EmailLog.objects.filter(
                status__in=['pending', 'retry'],
                scheduled_at__lte=timezone.now()
            ).order_by('scheduled_at')
            
            self.stdout.write(f'送信対象メール数: {pending_emails.count()}')
            for email in pending_emails:
                self.stdout.write(f'- {email.recipient_email}: {email.subject}')
        else:
            self.stdout.write('スケジュールメール送信を開始します...')
            success_count, failed_count = process_scheduled_emails()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'メール送信完了: 成功 {success_count}件, 失敗 {failed_count}件'
                )
            )