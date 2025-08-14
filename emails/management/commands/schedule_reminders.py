from django.core.management.base import BaseCommand
from emails.utils import schedule_reminder_emails


class Command(BaseCommand):
    help = '予約リマインダーメールをスケジュールします'
    
    def handle(self, *args, **options):
        self.stdout.write('リマインダーメールのスケジューリングを開始します...')
        
        try:
            schedule_reminder_emails()
            self.stdout.write(
                self.style.SUCCESS('リマインダーメールのスケジューリングが完了しました。')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'リマインダーメールのスケジューリングに失敗しました: {str(e)}')
            )