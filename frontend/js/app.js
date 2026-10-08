const App = {
    currentAssessmentId: null,
    currentAssessment: null,

    init() {
        this.bindEvents();
        this.loadAssessments();
    },

    bindEvents() {
        document.getElementById('btnNewAssessment').addEventListener('click', () => this.createAssessment());
        document.getElementById('btnBackToList').addEventListener('click', () => this.showLandingView());
        document.getElementById('btnDeleteAssessment').addEventListener('click', () => this.deleteAssessment());

        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.currentTarget.dataset.tab));
        });

        this.setupUpload('guideline');
        this.setupUpload('application');

        document.getElementById('btnReuploadGuideline').addEventListener('click', () => {
            document.getElementById('guidelineFile').click();
        });
        document.getElementById('btnReuploadApplication').addEventListener('click', () => {
            document.getElementById('applicationFile').click();
        });

        document.getElementById('btnAnalyze').addEventListener('click', () => this.runAnalysis());

        document.querySelectorAll('#panel-requirements .filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.filterRequirements(e.currentTarget.dataset.filter, e.currentTarget));
        });

        document.querySelectorAll('#panel-mappings .filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.filterMappings(e.currentTarget.dataset.filter, e.currentTarget));
        });

        document.getElementById('btnAddDoc').addEventListener('click', () => this.showAddDocModal());
        document.getElementById('btnCancelDoc').addEventListener('click', () => this.hideAddDocModal());
        document.getElementById('btnSaveDoc').addEventListener('click', () => this.saveNewDoc());

        document.getElementById('btnRegenSummary').addEventListener('click', () => this.regenerateSummary());
        document.getElementById('assessmentTitle').addEventListener('change', (e) => this.updateTitle(e.target.value));
    },

    setupUpload(type) {
        const dropzone = document.getElementById(`${type}Dropzone`);
        const fileInput = document.getElementById(`${type}File`);

        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this.handleFileUpload(type, e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.handleFileUpload(type, e.target.files[0]);
            }
        });
    },

    showLandingView() {
        document.getElementById('landingView').classList.add('active');
        document.getElementById('workspaceView').classList.remove('active');
        this.currentAssessmentId = null;
        this.currentAssessment = null;
        this.loadAssessments();
    },

    showWorkspaceView() {
        document.getElementById('landingView').classList.remove('active');
        document.getElementById('workspaceView').classList.add('active');
    },

    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');

        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.getElementById(`panel-${tabName}`).classList.add('active');

        if (tabName === 'requirements') this.renderRequirements();
        if (tabName === 'mappings') this.renderMappings();
        if (tabName === 'documents') this.renderDocuments();
        if (tabName === 'summary') this.renderSummary();
    },

    showLoading(title = 'Analyzing...', message = 'AI is reviewing your documents. This may take a moment.') {
        document.getElementById('loadingTitle').textContent = title;
        document.getElementById('loadingMessage').textContent = message;
        document.getElementById('loadingOverlay').style.display = 'flex';
    },

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    },

    async loadAssessments() {
        try {
            const assessments = await API.listAssessments();
            const grid = document.getElementById('assessmentsGrid');
            const section = document.getElementById('assessmentsListSection');

            if (assessments.length === 0) {
                section.style.display = 'none';
                return;
            }

            section.style.display = 'block';
            grid.innerHTML = assessments.map(a => Components.assessmentCard(a)).join('');

            grid.querySelectorAll('.assessment-card').forEach(card => {
                card.addEventListener('click', () => this.openAssessment(card.dataset.id));
            });
        } catch (err) {
            Components.showToast('Failed to load assessments', 'error');
        }
    },

    async createAssessment() {
        try {
            const assessment = await API.createAssessment('Untitled Assessment');
            this.currentAssessmentId = assessment.id;
            await this.openAssessment(assessment.id);
            Components.showToast('Assessment created', 'success');
        } catch (err) {
            Components.showToast('Failed to create assessment', 'error');
        }
    },

    async openAssessment(id) {
        try {
            this.showLoading('Loading...', 'Fetching assessment details.');
            const assessment = await API.getAssessment(id);
            this.currentAssessmentId = id;
            this.currentAssessment = assessment;
            this.populateWorkspace(assessment);
            this.showWorkspaceView();
            this.hideLoading();
        } catch (err) {
            this.hideLoading();
            Components.showToast('Failed to open assessment', 'error');
        }
    },

    async deleteAssessment() {
        if (!this.currentAssessmentId) return;
        if (!confirm('Delete this assessment? This cannot be undone.')) return;
        try {
            await API.deleteAssessment(this.currentAssessmentId);
            Components.showToast('Assessment deleted', 'success');
            this.showLandingView();
        } catch (err) {
            Components.showToast('Failed to delete assessment', 'error');
        }
    },

    async updateTitle(newTitle) {
        if (this.currentAssessment) {
            this.currentAssessment.title = newTitle;
        }
    },

    populateWorkspace(assessment) {
        document.getElementById('assessmentTitle').value = assessment.title;

        if (assessment.is_stale) {
            document.getElementById('staleBadge').style.display = 'inline';
            document.getElementById('staleBadge').title = assessment.stale_reason || 'Documents have changed';
        } else {
            document.getElementById('staleBadge').style.display = 'none';
        }

        const statusBadge = document.getElementById('statusBadge');
        statusBadge.textContent = assessment.analysis_status === 'completed' ? '✓ Analyzed' :
            assessment.analysis_status === 'running' ? '⏳ Running' :
            assessment.analysis_status === 'failed' ? '✗ Failed' : 'Ready';

        if (assessment.guideline_filename) {
            document.getElementById('guidelineDropzone').style.display = 'none';
            document.getElementById('guidelineInfo').style.display = 'flex';
            document.getElementById('guidelineFileName').textContent = assessment.guideline_filename;
            document.getElementById('guidelineVersion').textContent = `Version ${assessment.guideline_version}`;
            document.getElementById('guidelineStatus').textContent = '✓ Uploaded';
            document.getElementById('guidelineStatus').classList.add('uploaded');
            document.getElementById('guidelineCard').classList.add('uploaded');
        } else {
            document.getElementById('guidelineDropzone').style.display = '';
            document.getElementById('guidelineInfo').style.display = 'none';
            document.getElementById('guidelineStatus').textContent = 'Not uploaded';
            document.getElementById('guidelineStatus').classList.remove('uploaded');
            document.getElementById('guidelineCard').classList.remove('uploaded');
        }

        if (assessment.application_filename) {
            document.getElementById('applicationDropzone').style.display = 'none';
            document.getElementById('applicationInfo').style.display = 'flex';
            document.getElementById('applicationFileName').textContent = assessment.application_filename;
            document.getElementById('applicationVersion').textContent = `Version ${assessment.application_version}`;
            document.getElementById('applicationStatus').textContent = '✓ Uploaded';
            document.getElementById('applicationStatus').classList.add('uploaded');
            document.getElementById('applicationCard').classList.add('uploaded');
        } else {
            document.getElementById('applicationDropzone').style.display = '';
            document.getElementById('applicationInfo').style.display = 'none';
            document.getElementById('applicationStatus').textContent = 'Not uploaded';
            document.getElementById('applicationStatus').classList.remove('uploaded');
            document.getElementById('applicationCard').classList.remove('uploaded');
        }

        const btnAnalyze = document.getElementById('btnAnalyze');
        const analyzeHint = document.querySelector('.analyze-hint');
        if (assessment.guideline_filename && assessment.application_filename) {
            btnAnalyze.disabled = false;
            analyzeHint.textContent = assessment.analysis_status === 'completed'
                ? 'Re-run analysis to refresh results'
                : 'Ready to analyze';
        } else {
            btnAnalyze.disabled = true;
            analyzeHint.textContent = 'Upload both documents to enable analysis';
        }

        const reqCount = assessment.requirements ? assessment.requirements.length : 0;
        if (reqCount > 0) {
            document.getElementById('reqCount').style.display = 'inline-flex';
            document.getElementById('reqCount').textContent = reqCount;
        }
        let mapCount = 0;
        if (assessment.requirements) {
            assessment.requirements.forEach(r => { mapCount += (r.mappings ? r.mappings.length : 0); });
        }
        if (mapCount > 0) {
            document.getElementById('mapCount').style.display = 'inline-flex';
            document.getElementById('mapCount').textContent = mapCount;
        }

        if (assessment.analysis_status === 'completed') {
            this.loadCompleteness();
        }

        this.renderRequirements();
        this.renderDocuments();
    },

    async handleFileUpload(type, file) {
        if (!this.currentAssessmentId) return;
        this.showLoading('Uploading...', `Processing ${file.name}...`);

        try {
            let result;
            if (type === 'guideline') {
                result = await API.uploadGuideline(this.currentAssessmentId, file);
            } else {
                result = await API.uploadApplication(this.currentAssessmentId, file);
            }

            this.currentAssessment = await API.getAssessment(this.currentAssessmentId);
            this.populateWorkspace(this.currentAssessment);

            Components.showToast(`${type === 'guideline' ? 'Guideline' : 'Application'} uploaded (${result.text_length.toLocaleString()} chars)`, 'success');

            if (result.is_stale) {
                Components.showToast(result.stale_reason, 'warning');
            }
        } catch (err) {
            Components.showToast(`Upload failed: ${err.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    },

    async runAnalysis() {
        if (!this.currentAssessmentId) return;
        this.showLoading('Running AI Analysis', 'Extracting requirements, mapping evidence, and identifying gaps. This may take 30-60 seconds...');

        try {
            const result = await API.runAnalysis(this.currentAssessmentId);

            if (result.status === 'completed') {
                Components.showToast('Analysis completed successfully!', 'success');
            } else {
                Components.showToast(`Analysis failed: ${result.message}`, 'error');
            }

            this.currentAssessment = await API.getAssessment(this.currentAssessmentId);
            this.populateWorkspace(this.currentAssessment);
            this.switchTab('requirements');
        } catch (err) {
            Components.showToast(`Analysis error: ${err.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    },

    async loadCompleteness() {
        if (!this.currentAssessmentId) return;
        try {
            const score = await API.getCompleteness(this.currentAssessmentId);
            this.renderScore(score);
        } catch (err) {
            console.error('Failed to load completeness:', err);
        }
    },

    renderScore(score) {
        const card = document.getElementById('scoreCard');
        card.style.display = 'block';

        document.getElementById('mandatoryPct').textContent = `${score.mandatory_pct}%`;
        document.getElementById('mandatoryDetail').textContent = `${score.mandatory_met}/${score.mandatory_total}`;
        document.getElementById('recommendedPct').textContent = `${score.recommended_pct}%`;
        document.getElementById('recommendedDetail').textContent = `${score.recommended_met}/${score.recommended_total}`;
        document.getElementById('overallPct').textContent = `${score.overall_pct}%`;
        document.getElementById('overallDetail').textContent = `${score.overall_met}/${score.overall_total}`;

        Components.updateScoreRing('mandatoryProgress', score.mandatory_pct);
        Components.updateScoreRing('recommendedProgress', score.recommended_pct);
        Components.updateScoreRing('overallProgress', score.overall_pct);

        const total = score.reviewed_count + score.pending_count;
        const pct = total > 0 ? (score.reviewed_count / total * 100) : 0;
        document.getElementById('reviewProgressFill').style.width = `${pct}%`;
        document.getElementById('reviewProgressLabel').textContent = `${score.reviewed_count}/${total} reviewed`;
    },

    renderRequirements() {
        const list = document.getElementById('requirementsList');
        const reqs = this.currentAssessment?.requirements || [];

        if (reqs.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>No requirements extracted yet. Upload documents and run analysis.</p></div>';
            return;
        }

        list.innerHTML = reqs.map((r, i) => Components.requirementItem(r, i)).join('');
    },

    filterRequirements(filter, btn) {
        btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const items = document.querySelectorAll('#requirementsList .requirement-item');
        items.forEach(item => {
            if (filter === 'all') {
                item.style.display = '';
            } else if (filter === 'mandatory') {
                item.style.display = item.dataset.mandatory === 'true' ? '' : 'none';
            } else {
                item.style.display = item.dataset.mandatory === 'false' ? '' : 'none';
            }
        });
    },

    renderMappings() {
        const list = document.getElementById('mappingsList');
        const reqs = this.currentAssessment?.requirements || [];

        if (reqs.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>No mappings to review. Run analysis first.</p></div>';
            return;
        }

        let html = '';
        reqs.forEach((req, i) => {
            if (req.mappings && req.mappings.length > 0) {
                req.mappings.forEach(mapping => {
                    html += Components.mappingItem(req, mapping, i);
                });
            }
        });

        if (!html) {
            list.innerHTML = '<div class="empty-state"><p>No mappings found. The analysis may not have found any evidence.</p></div>';
            return;
        }

        list.innerHTML = html;
    },

    filterMappings(filter, btn) {
        btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const items = document.querySelectorAll('#mappingsList .mapping-item');
        items.forEach(item => {
            if (filter === 'all') {
                item.style.display = '';
            } else {
                item.style.display = item.dataset.userStatus === filter ? '' : 'none';
            }
        });
    },

    async updateMapping(mappingId, status) {
        if (!this.currentAssessmentId) return;
        try {
            await API.updateMapping(this.currentAssessmentId, mappingId, {
                user_status: status,
            });

            this.currentAssessment = await API.getAssessment(this.currentAssessmentId);
            this.renderMappings();
            this.loadCompleteness();

            Components.showToast(`Mapping ${status}`, 'success');
        } catch (err) {
            Components.showToast(`Failed to update: ${err.message}`, 'error');
        }
    },

    showCorrectModal(mappingId) {
        const newExcerpt = prompt('Enter the correct evidence excerpt (or leave blank to keep current):');
        const newStrength = prompt('Enter evidence strength (met / partial / missing / ambiguous):');

        if (newStrength && ['met', 'partial', 'missing', 'ambiguous'].includes(newStrength)) {
            this.correctMapping(mappingId, newExcerpt, newStrength);
        } else if (newStrength) {
            Components.showToast('Invalid strength. Use: met, partial, missing, or ambiguous', 'error');
        }
    },

    async correctMapping(mappingId, excerpt, strength) {
        if (!this.currentAssessmentId) return;
        try {
            const data = {
                user_status: 'corrected',
                evidence_strength: strength,
            };
            if (excerpt) data.application_excerpt = excerpt;

            await API.updateMapping(this.currentAssessmentId, mappingId, data);

            this.currentAssessment = await API.getAssessment(this.currentAssessmentId);
            this.renderMappings();
            this.loadCompleteness();

            Components.showToast('Mapping corrected', 'success');
        } catch (err) {
            Components.showToast(`Failed to correct: ${err.message}`, 'error');
        }
    },

    async saveNotes(input) {
        const mappingId = input.dataset.mappingId;
        if (!this.currentAssessmentId || !mappingId) return;
        try {
            let currentStatus = 'confirmed';
            const item = input.closest('.mapping-item');
            if (item) currentStatus = item.dataset.userStatus;
            if (currentStatus === 'pending') currentStatus = 'confirmed';

            await API.updateMapping(this.currentAssessmentId, mappingId, {
                user_status: currentStatus,
                user_notes: input.value,
            });
            Components.showToast('Notes saved', 'info');
        } catch (err) {
            Components.showToast(`Failed to save notes: ${err.message}`, 'error');
        }
    },

    renderDocuments() {
        const list = document.getElementById('documentsList');
        const docs = this.currentAssessment?.supporting_docs || [];

        if (docs.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>No supporting documents tracked yet.</p></div>';
            return;
        }

        list.innerHTML = docs.map(d => Components.documentItem(d)).join('');
    },

    showAddDocModal() {
        document.getElementById('addDocModal').style.display = 'flex';
        document.getElementById('newDocName').value = '';
        document.getElementById('newDocDesc').value = '';
        document.getElementById('newDocStatus').value = 'missing';
    },

    hideAddDocModal() {
        document.getElementById('addDocModal').style.display = 'none';
    },

    async saveNewDoc() {
        if (!this.currentAssessmentId) return;
        const name = document.getElementById('newDocName').value.trim();
        if (!name) {
            Components.showToast('Document name is required', 'error');
            return;
        }

        try {
            await API.addSupportingDoc(this.currentAssessmentId, {
                document_name: name,
                description: document.getElementById('newDocDesc').value.trim(),
                status: document.getElementById('newDocStatus').value,
            });

            this.hideAddDocModal();
            this.currentAssessment = await API.getAssessment(this.currentAssessmentId);
            this.renderDocuments();
            Components.showToast('Document added', 'success');
        } catch (err) {
            Components.showToast(`Failed to add: ${err.message}`, 'error');
        }
    },

    async updateDocStatus(docId, status) {
        if (!this.currentAssessmentId) return;
        try {
            await API.updateSupportingDoc(this.currentAssessmentId, docId, { status });
            Components.showToast('Document status updated', 'info');
        } catch (err) {
            Components.showToast(`Failed to update: ${err.message}`, 'error');
        }
    },

    renderSummary() {
        const container = document.getElementById('summaryContent');
        const summary = this.currentAssessment?.summary_report;

        if (!summary) {
            container.innerHTML = '<div class="empty-state"><p>No summary generated yet. Run analysis first.</p></div>';
            return;
        }

        container.innerHTML = Components.markdownToHtml(summary);
    },

    async regenerateSummary() {
        if (!this.currentAssessmentId) return;
        this.showLoading('Regenerating Summary', 'Creating an updated completeness report...');

        try {
            const result = await API.getSummary(this.currentAssessmentId, true);
            this.currentAssessment.summary_report = result.summary;
            this.renderSummary();
            Components.showToast('Summary regenerated', 'success');
        } catch (err) {
            Components.showToast(`Failed: ${err.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());
