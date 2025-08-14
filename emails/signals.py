from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from bookings.models import Booking
from .utils import send_booking_confirmation_email, send_admin_new_booking_email, send_booking_status_changed_email
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Booking)
def booking_created_handler(sender, instance, created, **kwargs):
    """新規予約作成時の処理"""
    if created:
        try:
            # 顧客向け予約確認メール
            send_booking_confirmation_email(instance)
            
            # 管理者向け新規予約通知メール
            send_admin_new_booking_email(instance)
            
            logger.info(f"予約作成メール送信完了: {instance}")
            
        except Exception as e:
            logger.error(f"予約作成メール送信エラー: {instance} - {str(e)}")


@receiver(pre_save, sender=Booking)
def booking_status_changed_handler(sender, instance, **kwargs):
    """予約ステータス変更時の処理"""
    if instance.pk:  # 既存の予約の場合
        try:
            old_booking = Booking.objects.get(pk=instance.pk)
            if old_booking.status != instance.status:
                # ステータスが変更された場合
                instance._old_status = old_booking.status
                instance._status_changed = True
            else:
                instance._status_changed = False
        except Booking.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=Booking)
def booking_status_updated_handler(sender, instance, created, **kwargs):
    """予約ステータス更新後の処理"""
    if not created and getattr(instance, '_status_changed', False):
        try:
            old_status = getattr(instance, '_old_status', None)
            if old_status:
                send_booking_status_changed_email(instance, old_status, instance.status)
                logger.info(f"ステータス変更メール送信完了: {instance} ({old_status} -> {instance.status})")
                
        except Exception as e:
            logger.error(f"ステータス変更メール送信エラー: {instance} - {str(e)}")