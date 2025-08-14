// メール設定管理画面のJavaScript

document.addEventListener('DOMContentLoaded', function() {
    // テストメール送信ボタンを追加
    const saveButtons = document.querySelector('.submit-row');
    if (saveButtons) {
        const testEmailButton = document.createElement('input');
        testEmailButton.type = 'submit';
        testEmailButton.name = '_test_email';
        testEmailButton.value = 'テストメール送信';
        testEmailButton.className = 'default';
        testEmailButton.style.marginLeft = '10px';
        testEmailButton.style.backgroundColor = '#17a2b8';
        testEmailButton.style.color = 'white';
        
        testEmailButton.addEventListener('click', function(e) {
            if (!confirm('管理者メールアドレスにテストメールを送信しますか？')) {
                e.preventDefault();
            }
        });
        
        saveButtons.appendChild(testEmailButton);
    }
    
    // リマインダー時間の説明を追加
    const reminderField = document.querySelector('#id_reminder_hours_before');
    if (reminderField) {
        const helpText = document.createElement('div');
        helpText.className = 'help';
        helpText.innerHTML = '<strong>例:</strong> 24,2 (24時間前と2時間前), 1 (1時間前のみ)';
        reminderField.parentNode.appendChild(helpText);
    }
    
    // メール署名のプレビュー
    const signatureField = document.querySelector('#id_signature');
    if (signatureField) {
        const preview = document.createElement('div');
        preview.style.marginTop = '10px';
        preview.style.padding = '10px';
        preview.style.backgroundColor = '#f8f9fa';
        preview.style.border = '1px solid #ddd';
        preview.style.borderRadius = '3px';
        preview.style.whiteSpace = 'pre-line';
        preview.style.fontFamily = 'monospace';
        preview.style.fontSize = '12px';
        
        const updatePreview = function() {
            preview.textContent = signatureField.value || '(プレビューなし)';
        };
        
        signatureField.addEventListener('input', updatePreview);
        updatePreview();
        
        const previewLabel = document.createElement('label');
        previewLabel.textContent = 'プレビュー:';
        previewLabel.style.display = 'block';
        previewLabel.style.marginTop = '10px';
        previewLabel.style.fontWeight = 'bold';
        
        signatureField.parentNode.appendChild(previewLabel);
        signatureField.parentNode.appendChild(preview);
    }
});