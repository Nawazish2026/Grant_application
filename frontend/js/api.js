const API = {
    BASE: '/api/assessments',

    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
                    ...options.headers,
                },
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(err.detail || `HTTP ${response.status}`);
            }
            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error(`API Error: ${error.message}`);
            throw error;
        }
    },

    createAssessment(title = 'Untitled Assessment') {
        return this.request(this.BASE, {
            method: 'POST',
            body: JSON.stringify({ title }),
        });
    },

    listAssessments() {
        return this.request(this.BASE);
    },

    getAssessment(id) {
        return this.request(`${this.BASE}/${id}`);
    },

    deleteAssessment(id) {
        return this.request(`${this.BASE}/${id}`, { method: 'DELETE' });
    },

    uploadGuideline(assessmentId, file) {
        const form = new FormData();
        form.append('file', file);
        return this.request(`${this.BASE}/${assessmentId}/upload-guideline`, {
            method: 'POST',
            body: form,
        });
    },

    uploadApplication(assessmentId, file) {
        const form = new FormData();
        form.append('file', file);
        return this.request(`${this.BASE}/${assessmentId}/upload-application`, {
            method: 'POST',
            body: form,
        });
    },

    runAnalysis(assessmentId) {
        return this.request(`${this.BASE}/${assessmentId}/analyze`, {
            method: 'POST',
        });
    },

    updateMapping(assessmentId, mappingId, data) {
        return this.request(`${this.BASE}/${assessmentId}/mappings/${mappingId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    getCompleteness(assessmentId) {
        return this.request(`${this.BASE}/${assessmentId}/completeness`);
    },

    getSummary(assessmentId, regenerate = false) {
        const q = regenerate ? '?regenerate=true' : '';
        return this.request(`${this.BASE}/${assessmentId}/summary${q}`);
    },

    checkStaleness(assessmentId) {
        return this.request(`${this.BASE}/${assessmentId}/staleness`);
    },

    addSupportingDoc(assessmentId, data) {
        return this.request(`${this.BASE}/${assessmentId}/supporting-docs`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    updateSupportingDoc(assessmentId, docId, data) {
        return this.request(`${this.BASE}/${assessmentId}/supporting-docs/${docId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },
};
