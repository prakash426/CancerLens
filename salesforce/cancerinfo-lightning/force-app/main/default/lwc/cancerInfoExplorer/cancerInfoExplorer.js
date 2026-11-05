import { LightningElement, api, wire } from 'lwc';
import { refreshApex } from '@salesforce/apex';
import getCancers from '@salesforce/apex/CancerInfoController.getCancers';
import { buildPromptSuggestions, cancerMeta, reduceError, resolveCancer } from 'c/cancerInfoUtils';

/**
 * CancerInfo Explorer - Home page / App page tile.
 * Pick a cancer (type-ahead over the live CancerInfo API list), optionally ask a question or
 * paste a claim, and view a source-linked profile. Educational information only.
 */
export default class CancerInfoExplorer extends LightningElement {
    @api cardTitle = 'CancerInfo Explorer';

    cancers = [];
    cancersLoading = true;
    cancersError;
    _wiredCancers;

    mode = 'question';
    cancerText = '';
    selectedCancer;
    promptText = '';
    formError;
    request;

    @wire(getCancers)
    wiredCancers(result) {
        this._wiredCancers = result;
        if (result.data) {
            this.cancers = result.data;
            this.cancersError = undefined;
            this.cancersLoading = false;
        } else if (result.error) {
            this.cancersError = reduceError(result.error);
            this.cancersLoading = false;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // View state
    // ---------------------------------------------------------------------------------------------

    get heroTitle() {
        return this.cardTitle || 'CancerInfo Explorer';
    }

    get cancerOptions() {
        return this.cancers.map((c) => ({
            value: c.slug,
            label: c.name,
            meta: cancerMeta(c),
            keywords: [...(c.aliases || []), c.site || '', (c.slug || '').replace(/-/g, ' ')],
            icon: 'utility:ribbon'
        }));
    }

    get promptOptions() {
        return buildPromptSuggestions(this.selectedCancer, this.mode);
    }

    get isClaimMode() {
        return this.mode === 'claim';
    }

    get questionChecked() {
        return this.isClaimMode ? 'false' : 'true';
    }

    get claimChecked() {
        return this.isClaimMode ? 'true' : 'false';
    }

    get questionButtonClass() {
        return `ci-mode__btn${this.isClaimMode ? '' : ' ci-mode__btn_active'}`;
    }

    get claimButtonClass() {
        return `ci-mode__btn${this.isClaimMode ? ' ci-mode__btn_active' : ''}`;
    }

    get promptLabel() {
        return this.isClaimMode ? 'Claim to check (optional)' : 'Your question (optional)';
    }

    get promptIcon() {
        return this.isClaimMode ? 'utility:quotation_marks' : 'utility:question';
    }

    get promptPlaceholder() {
        return this.isClaimMode
            ? 'Paste or type a claim, e.g. “Surgery is the only treatment”'
            : 'Type a question, e.g. “What are the early symptoms?”';
    }

    get promptHelp() {
        return this.isClaimMode
            ? 'CancerInfo finds passages from trusted health organisations related to the claim. It does not label claims true or false.'
            : 'Suggestions are based on the topics available for the selected cancer.';
    }

    get cancerPlaceholder() {
        return this.cancersLoading ? 'Loading cancer types…' : 'Start typing, e.g. breast, bowel, leukemia';
    }

    get cancerDisabled() {
        return this.cancersLoading || Boolean(this.cancersError);
    }

    get searchLabel() {
        return this.isClaimMode ? 'Check Claim' : 'Get Information';
    }

    get searchDisabled() {
        return this.cancerDisabled || !this.cancerText.trim();
    }

    get showReset() {
        return Boolean(this.request || this.cancerText || this.promptText);
    }

    // ---------------------------------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------------------------------

    handleModeClick(event) {
        const mode = event.currentTarget.dataset.mode;
        if (mode && mode !== this.mode) {
            this.mode = mode;
            this.promptText = '';
        }
    }

    handleCancerText(event) {
        this.cancerText = event.detail.value || '';
        this.formError = undefined;
        if (this.selectedCancer && this.cancerText !== this.selectedCancer.name) {
            this.selectedCancer = undefined;
        }
    }

    handleCancerSelect(event) {
        const cancer = this.cancers.find((c) => c.slug === event.detail.value);
        if (cancer) {
            this.selectedCancer = cancer;
            this.cancerText = cancer.name;
            this.formError = undefined;
            const prompt = this.refs.prompt;
            if (prompt) {
                prompt.focus();
            }
        }
    }

    handlePromptText(event) {
        this.promptText = event.detail.value || '';
    }

    handlePromptSelect(event) {
        this.promptText = event.detail.label || '';
    }

    handleSearch() {
        if (this.cancerDisabled) {
            return;
        }
        const cancer = this.selectedCancer || resolveCancer(this.cancers, this.cancerText);
        if (!cancer) {
            this.formError = 'Please choose a cancer type from the suggestions.';
            const field = this.refs.cancer;
            if (field) {
                field.focus();
            }
            return;
        }
        this.formError = undefined;
        this.selectedCancer = cancer;
        this.cancerText = cancer.name;
        this.request = {
            slug: cancer.slug,
            text: this.promptText.trim(),
            mode: this.mode,
            key: Date.now()
        };
    }

    handleReset() {
        this.cancerText = '';
        this.selectedCancer = undefined;
        this.promptText = '';
        this.formError = undefined;
        this.request = undefined;
    }

    handleRetryCancers() {
        this.cancersLoading = true;
        this.cancersError = undefined;
        refreshApex(this._wiredCancers).catch((e) => {
            this.cancersError = reduceError(e);
            this.cancersLoading = false;
        });
    }
}
