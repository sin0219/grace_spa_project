from django.core.management.base import BaseCommand
from bookings.models import BusinessHours, BookingSettings

class Command(BaseCommand):
    help = '営業時間と予約設定の初期データを作成します'

    def handle(self, *args, **options):
        # 営業時間の初期設定
        default_hours = [
            (0, True, '09:00', '20:00', '19:00'),   # 月曜日
            (1, True, '09:00', '20:00', '19:00'),   # 火曜日
            (2, True, '09:00', '20:00', '19:00'),   # 水曜日
            (3, True, '09:00', '20:00', '19:00'),   # 木曜日
            (4, True, '09:00', '20:00', '19:00'),   # 金曜日
            (5, True, '09:00', '20:00', '19:00'),   # 土曜日
            (6, False, '09:00', '20:00', '19:00'),  # 日曜日（定休日）
        ]
        
        created_count = 0
        for weekday, is_open, open_time, close_time, last_booking in default_hours:
            business_hour, created = BusinessHours.objects.get_or_create(
                weekday=weekday,
                defaults={
                    'is_open': is_open,
                    'open_time': open_time,
                    'close_time': close_time,
                    'last_booking_time': last_booking,
                }
            )
            if created:
                created_count += 1
                weekday_name = dict(BusinessHours.WEEKDAY_CHOICES)[weekday]
                if is_open:
                    self.stdout.write(
                        self.style.SUCCESS(f'{weekday_name}: {open_time}-{close_time} を作成しました')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'{weekday_name}: 定休日 を作成しました')
                    )
        
        # 予約設定の初期作成
        booking_settings, created = BookingSettings.objects.get_or_create(
            id=1,
            defaults={
                'booking_interval_minutes': 30,
                'treatment_buffer_minutes': 15,
                'advance_booking_days': 90,
                'same_day_booking_cutoff': '12:00',
                'default_treatment_duration': 90,
                'allow_same_time_bookings': False,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('予約設定を作成しました')
            )
            created_count += 1
        
        if created_count == 0:
            self.stdout.write(
                self.style.WARNING('営業時間と予約設定は既に存在します')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'合計 {created_count} 件の設定を作成しました')
            )