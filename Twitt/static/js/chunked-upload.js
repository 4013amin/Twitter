async function normalUpload() {
    const formData = new FormData();
    formData.append('content', document.getElementById('tweet-content').value);
    if (selectedFile) {
        formData.append(selectedFileType, selectedFile);
    }

    const response = await fetch('{% url "create_tweet" %}', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    });

    // اول متن پاسخ را دریافت کنیم
    const text = await response.text();
    console.log('Response status:', response.status);
    console.log('Response text:', text.substring(0, 500)); // فقط ۵۰۰ کاراکتر اول

    // بررسی آیا JSON است
    let data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        // اگر JSON نیست، خطا را با پیام بهتر نشان بده
        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
            throw new Error('سرور یک صفحه HTML برگرداند. احتمالاً خطایی در فرم وجود دارد یا CSRF token مشکل دارد.');
        }
        throw new Error('پاسخ نامعتبر از سرور: ' + text.substring(0, 100));
    }

    if (!response.ok) {
        throw new Error(data.error || 'خطا در ارسال - کد: ' + response.status);
    }

    if (data.success) {
        window.location.reload();
    } else {
        throw new Error(data.error || 'خطای ناشناخته');
    }
}

async function submitTextOnly() {
    const formData = new FormData();
    formData.append('content', document.getElementById('tweet-content').value);

    const response = await fetch('{% url "create_tweet" %}', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    });

    const text = await response.text();
    console.log('Response status:', response.status);
    console.log('Response text:', text.substring(0, 500));

    let data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
            throw new Error('سرور یک صفحه HTML برگرداند. احتمالاً خطایی در فرم وجود دارد.');
        }
        throw new Error('پاسخ نامعتبر از سرور');
    }

    if (!response.ok) {
        throw new Error(data.error || 'خطا در ارسال - کد: ' + response.status);
    }

    if (data.success) {
        window.location.reload();
    } else {
        throw new Error(data.error || 'خطای ناشناخته');
    }
}

async function submitWithFilePath(filePath) {
    const formData = new FormData();
    formData.append('content', document.getElementById('tweet-content').value);
    formData.append('file_path', filePath);
    formData.append('tweet_type', selectedFileType);

    const response = await fetch('{% url "create_tweet" %}', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    });

    const text = await response.text();
    console.log('Response status:', response.status);
    console.log('Response text:', text.substring(0, 500));

    let data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
            throw new Error('سرور یک صفحه HTML برگرداند.');
        }
        throw new Error('پاسخ نامعتبر از سرور');
    }

    if (!response.ok) {
        throw new Error(data.error || 'خطا در ارسال توییت - کد: ' + response.status);
    }

    if (data.success) {
        window.location.reload();
    } else {
        throw new Error(data.error || 'خطای ناشناخته');
    }
}