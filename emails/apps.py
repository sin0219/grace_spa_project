from django.apps import AppConfig


class EmailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emails'
    verbose_name = 'メール機能'
    
    def ready(self):
        # シグナルをインポート
        import emails.signals