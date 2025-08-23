# bookings/utils/language.py
# 新しいフォルダとファイルを作成してください

def get_language_from_url(request):
    """
    URLパスから言語を判定する
    /en/ で始まる場合は 'en'、それ以外は 'ja' を返す
    """
    if request.path.startswith('/en/'):
        return 'en'
    return 'ja'

def get_language(request=None):
    """
    現在の言語を取得する関数
    セッション、URL、デフォルトの順で判定
    """
    if request:
        # セッションから言語を取得
        session_lang = request.session.get('language')
        if session_lang in ['ja', 'en']:
            return session_lang
        
        # URLから言語を判定
        url_lang = get_language_from_url(request)
        # セッションに保存
        request.session['language'] = url_lang
        return url_lang
    
    # デフォルトは日本語
    return 'ja'

def set_language(request, language):
    """
    言語をセッションに保存する
    """
    if language in ['ja', 'en']:
        request.session['language'] = language
    else:
        request.session['language'] = 'ja'

def get_language_name(language):
    """
    言語コードから言語名を取得
    """
    language_names = {
        'ja': '日本語',
        'en': 'English'
    }
    return language_names.get(language, '日本語')

def get_opposite_language(language):
    """
    反対の言語を取得
    """
    return 'en' if language == 'ja' else 'ja'