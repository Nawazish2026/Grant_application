const Components = {

    assessmentCard(assessment) {
        const date = assessment.updated_at
            ? new Date(assessment.updated_at).toLocaleDateString()
            : 'N/A';
        const statusClass = assessment.is_stale ? 'stale' : assessment.analysis_status;
        const statusText = assessment.is_stale ? '⚠️ Stale' : assessment.analysis_status;

        return `
            <div class="assessment-card" data-id="${assessment.id}">
                <div class="assessment-card-title">${this.escape(assessment.title)}</div>
                <div class="assessment-card-meta">
                    <span>${date}</span>
                    ${assessment.guideline_filename ? `<span>📄 ${this.escape(assessment.guideline_filename)}</span>` : ''}
                </div>
                <span class="assessment-card-status ${statusClass}">${statusText}</span>
            </div>
        `;
    },

    requirementItem(req, index) {
        const typeClass = req.is_mandatory ? 'badge-mandatory' : 'badge-recommended';
        const typeLabel = req.is_mandatory ? 'Mandatory' : 'Recommended';

        let strengthBadge = '';
        if (req.mappings && req.mappings.length > 0) {
            const strength = req.mappings[0].evidence_strength;
            strengthBadge = `<span class="badge badge-${strength}">${strength}</span>`;
        }

        return `
            <div class="requirement-item" data-mandatory="${req.is_mandatory}">
                <div class="req-header">
                    <span class="req-index">${index + 1}</span>
                    <div style="flex:1;">
                        <div class="req-category">${this.escape(req.category || 'General')}</div>
                        <div class="req-text">${this.escape(req.requirement_text)}</div>
                        ${req.source_reference ? `<div class="req-source">📍 ${this.escape(req.source_reference)}</div>` : ''}
                    </div>
                    <div class="req-badges">
                        <span class="badge ${typeClass}">${typeLabel}</span>
                        ${strengthBadge}
                    </div>
                </div>
            </div>
        `;
    },

    mappingItem(req, mapping, reqIndex) {
        const statusClass = `status-${mapping.user_status}`;

        let questionsHtml = '';
        if (req.clarification_questions && req.clarification_questions.length > 0) {
            const qList = req.clarification_questions
                .map(q => `<div class="mapping-question">❓ ${this.escape(q.question_text)}</div>`)
                .join('');
            questionsHtml = `
                <div class="mapping-questions">
                    <div class="mapping-questions-title">Clarification Questions</div>
                    ${qList}
                </div>
            `;
        }

        let claimsHtml = '';
        if (req.unsupported_claims && req.unsupported_claims.length > 0) {
            const cList = req.unsupported_claims
                .map(c => `<div class="mapping-claim">⚠️ <strong>${this.escape(c.claim_text)}</strong><br><small>${this.escape(c.explanation || '')}</small></div>`)
                .join('');
            claimsHtml = `
                <div class="mapping-claims">
                    <div class="mapping-claims-title">Unsupported Claims</div>
                    ${cList}
                </div>
            `;
        }

        return `
            <div class="mapping-item ${statusClass}" data-mapping-id="${mapping.id}" data-user-status="${mapping.user_status}">
                <div class="mapping-header">
                    <span class="req-index">${reqIndex + 1}</span>
                    <div class="mapping-req-text">${this.escape(req.requirement_text)}</div>
                    <div class="req-badges">
                        <span class="badge ${req.is_mandatory ? 'badge-mandatory' : 'badge-recommended'}">${req.is_mandatory ? 'Mandatory' : 'Recommended'}</span>
                        <span class="badge badge-${mapping.evidence_strength}">${mapping.evidence_strength}</span>
                    </div>
                </div>
                <div class="mapping-body">
                    <div class="mapping-section">
                        <div class="mapping-section-title">Application Evidence</div>
                        ${mapping.application_excerpt
                            ? `<div class="mapping-excerpt">"${this.escape(mapping.application_excerpt)}"</div>`
                            : `<div class="mapping-excerpt" style="color:var(--status-missing);">No evidence found</div>`
                        }
                        ${mapping.application_reference
                            ? `<div class="mapping-reference">📍 ${this.escape(mapping.application_reference)}</div>`
                            : ''
                        }
                    </div>
                    <div class="mapping-section">
                        <div class="mapping-section-title">AI Reasoning</div>
                        <div class="mapping-reasoning">${this.escape(mapping.ai_reasoning || 'N/A')}</div>
                    </div>
                </div>
                ${questionsHtml}
                ${claimsHtml}
                <div class="mapping-actions">
                    <button class="btn btn-confirm btn-sm" onclick="App.updateMapping('${mapping.id}', 'confirmed')" ${mapping.user_status === 'confirmed' ? 'disabled' : ''}>✓ Confirm</button>
                    <button class="btn btn-correct btn-sm" onclick="App.showCorrectModal('${mapping.id}')">✎ Correct</button>
                    <button class="btn btn-reject btn-sm" onclick="App.updateMapping('${mapping.id}', 'rejected')" ${mapping.user_status === 'rejected' ? 'disabled' : ''}>✗ Reject</button>
                    <input type="text" class="mapping-notes-input" placeholder="Add notes..." value="${this.escape(mapping.user_notes || '')}" data-mapping-id="${mapping.id}" onchange="App.saveNotes(this)">
                    ${mapping.user_status !== 'pending' ? `<span class="badge badge-${mapping.user_status === 'confirmed' ? 'met' : mapping.user_status === 'rejected' ? 'missing' : 'partial'}" style="margin-left:auto;">${mapping.user_status}</span>` : ''}
                </div>
            </div>
        `;
    },

    documentItem(doc) {
        const statusClass = doc.status === 'missing' ? 'status-missing' : doc.status === 'uploaded' ? 'status-uploaded' : '';
        return `
            <div class="document-item" data-doc-id="${doc.id}">
                <div class="doc-info">
                    <span class="doc-name">${this.escape(doc.document_name)}</span>
                    ${doc.description ? `<span class="doc-desc">${this.escape(doc.description)}</span>` : ''}
                    ${doc.required_by ? `<span class="doc-required-by">Required by: ${this.escape(doc.required_by)}</span>` : ''}
                </div>
                <select class="doc-status-select ${statusClass}" onchange="App.updateDocStatus('${doc.id}', this.value)" data-doc-id="${doc.id}">
                    <option value="missing" ${doc.status === 'missing' ? 'selected' : ''}>❌ Missing</option>
                    <option value="uploaded" ${doc.status === 'uploaded' ? 'selected' : ''}>✅ Uploaded</option>
                    <option value="not_applicable" ${doc.status === 'not_applicable' ? 'selected' : ''}>➖ N/A</option>
                </select>
            </div>
        `;
    },

    updateScoreRing(progressId, pct) {
        const el = document.getElementById(progressId);
        if (!el) return;
        const circumference = 264;
        const offset = circumference - (pct / 100) * circumference;
        el.style.strokeDashoffset = offset;
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(24px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    markdownToHtml(md) {
        if (!md) return '';
        return md
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^- (.*$)/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.*$)/gm, '<li>$2</li>')
            .replace(/(<li>.*<\/li>\n?)+/g, (match) => {
                return '<ul>' + match + '</ul>';
            })
            .replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>')
            .replace(/⚠️/g, '⚠️')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    },

    escape(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};
