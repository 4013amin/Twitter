// static/js/chunked-upload.js

class ChunkedUploader {
    constructor(options) {
        this.file = options.file;
        this.chunkSize = options.chunkSize || 5 * 1024 * 1024;
        this.uploadUrl = options.uploadUrl || '/upload/chunk/';
        this.fileType = options.fileType || 'video';
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});

        this.fileId = this.generateFileId();
    }

    generateFileId() {
        return 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async upload() {
        const totalChunks = Math.ceil(this.file.size / this.chunkSize);
        let chunkNumber = 0;
        let start = 0;

        while (start < this.file.size) {
            const chunk = this.file.slice(start, start + this.chunkSize);

            try {
                const response = await this.uploadChunk(chunk, chunkNumber, totalChunks);

                if (response.status === 'complete') {
                    this.onComplete(response);
                    return response;
                }

            } catch (error) {
                this.onError(error);
                throw error;
            }

            chunkNumber++;
            start += this.chunkSize;

            const progress = Math.round((chunkNumber / totalChunks) * 100);
            this.onProgress(progress);
        }
    }

    async uploadChunk(chunk, chunkNumber, totalChunks) {
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('chunkNumber', chunkNumber);
        formData.append('totalChunks', totalChunks);
        formData.append('fileId', this.fileId);
        formData.append('fileType', this.fileType);

        const response = await fetch(this.uploadUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        return await response.json();
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    }
}