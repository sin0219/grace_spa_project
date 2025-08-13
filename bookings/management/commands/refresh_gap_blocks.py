from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import BookingSettings, GapBlock
from datetime import timedelta

class Command(BaseCommand):
    help = '空白時間ブロックを再生成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='何日先まで処理するか（デフォルト: 予約設定の受付期間）'
        )
        
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='既存の自動生成ブロックをすべて削除してから再生成'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更せず、処理内容のみ表示'
        )

    def handle(self, *args, **options):
        try:
            settings = BookingSettings.get_current_settings()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'予約設定の取得に失敗しました: {e}')
            )
            return

        if not settings.auto_block_gaps:
            self.stdout.write(
                self.style.WARNING('空白時間自動ブロック機能が無効になっています。')
            )
            return

        # 処理日数を決定
        days = options['days'] or settings.advance_booking_days
        
        self.stdout.write(f'空白時間ブロックの再生成を開始します...')
        self.stdout.write(f'対象期間: 今日から{days}日先まで')
        self.stdout.write(f'最小空白時間: {settings.minimum_gap_minutes}分')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('※ DRY RUN モード: 実際の変更は行いません'))

        # 既存ブロックのクリア
        if options['clear_all']:
            existing_count = GapBlock.objects.filter(is_auto_generated=True).count()
            self.stdout.write(f'既存の自動生成ブロック {existing_count} 件を削除中...')
            
            if not options['dry_run']:
                GapBlock.objects.filter(is_auto_generated=True).delete()
            
            self.stdout.write(self.style.SUCCESS('既存ブロックを削除しました'))

        # 日付範囲を設定
        today = timezone.now().date()
        end_date = today + timedelta(days=days)
        
        total_days = (end_date - today).days + 1
        processed_days = 0
        created_blocks = 0
        
        current_date = today
        while current_date <= end_date:
            try:
                # その日のブロックを生成
                if not options['dry_run']:
                    # 既存の自動生成ブロックを削除
                    GapBlock.objects.filter(
                        block_date=current_date,
                        is_auto_generated=True
                    ).delete()
                    
                    # 新しいブロックを生成
                    settings._generate_gap_blocks_for_date(current_date)
                
                # 生成されたブロック数をカウント
                day_blocks = GapBlock.objects.filter(
                    block_date=current_date,
                    is_auto_generated=True
                ).count()
                
                created_blocks += day_blocks
                processed_days += 1
                
                if day_blocks > 0:
                    self.stdout.write(f'{current_date}: {day_blocks}件のブロックを生成')
                
                # プログレス表示
                if processed_days % 10 == 0:
                    progress = (processed_days / total_days) * 100
                    self.stdout.write(f'進捗: {processed_days}/{total_days} 日 ({progress:.1f}%)')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'{current_date} の処理でエラー: {e}')
                )
            
            current_date += timedelta(days=1)

        # 結果をサマリー表示
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('空白時間ブロック再生成完了'))
        self.stdout.write(f'処理日数: {processed_days} 日')
        self.stdout.write(f'生成ブロック数: {created_blocks} 件')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('※ DRY RUN モードのため実際の変更は行われませんでした'))
        
        # 設定情報の表示
        self.stdout.write('\n現在の設定:')
        self.stdout.write(f'  - 最小空白時間: {settings.minimum_gap_minutes}分')
        self.stdout.write(f'  - 営業開始前ブロック: {"有効" if settings.gap_block_before_opening else "無効"}')
        self.stdout.write(f'  - 予約間ブロック: {"有効" if settings.gap_block_between_bookings else "無効"}')
        self.stdout.write(f'  - 営業終了後ブロック: {"有効" if settings.gap_block_after_closing else "無効"}')
        
        # 今日のブロック例を表示
        today_blocks = GapBlock.objects.filter(
            block_date=today,
            is_auto_generated=True,
            is_active=True
        ).order_by('start_time')
        
        if today_blocks.exists():
            self.stdout.write(f'\n今日({today})のブロック例:')
            for block in today_blocks[:5]:  # 最初の5件のみ表示
                therapist_name = block.therapist.display_name if block.therapist else "全体"
                self.stdout.write(f'  - {block.start_time}-{block.end_time} ({therapist_name}): {block.reason}')
            
            if today_blocks.count() > 5:
                self.stdout.write(f'  ... 他 {today_blocks.count() - 5} 件')
        else:
            self.stdout.write(f'\n今日({today})にはブロックが生成されませんでした')

        self.stdout.write('\n管理画面でブロック状況を確認できます: /admin/bookings/gapblock/')