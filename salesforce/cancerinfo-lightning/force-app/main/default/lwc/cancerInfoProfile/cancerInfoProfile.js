import { LightningElement, api } from 'lwc';
import getCancerProfile from '@salesforce/apex/CancerInfoController.getCancerProfile';
import getSectionGroup from '@salesforce/apex/CancerInfoController.getSectionGroup';
import findEvidence from '@salesforce/apex/CancerInfoController.findEvidence';
import { reduceError, safeHref } from 'c/cancerInfoUtils';

const WIDE_BREAKPOINT = 880;
const BLOCKS_PER_SECTION = 3;
const MAX_SOURCES = 8;

/** Display metadata for each section group returned by CancerInfoController. */
const GROUP_META = {
    overview: { title: 'Overview (Plain Language)', icon: 'utility:knowledge_base', layout: 'bullets' },
    treatment: {
        title: 'General Treatment Approaches',
        subtitle: '(Neutral Educational Information)',
        icon: 'utility:heart',
        layout: 'bullets',
        boxed: true,
        note:
            'Trusted sources describe the following treatment approaches generally used in oncology. ' +
            'Individual care plans depend strictly on stage, tumour pathology and a doctor’s consultation.'
    },
    symptoms: { title: 'Symptoms Described by Authoritative Sources', icon: 'utility:activity', layout: 'tiles' },
    diagnosis: { title: 'Common Diagnostic & Staging Procedures', icon: 'utility:shield', layout: 'bullets' },
    causes: { title: 'Causes, Risk Factors & Prevention', icon: 'utility:warning', layout: 'bullets' },
    living: { title: 'Living With Cancer & Supportive Care', icon: 'utility:people', layout: 'bullets' },
    outlook: { title: 'Outlook & Statistics', icon: 'utility:trending', layout: 'bullets' },
    research: { title: 'Current Research Highlights', icon: 'utility:sparkles', layout: 'compact' }
};

export default class CancerInfoProfile extends LightningElement {
    _request;
    _token = 0;
    _connected = false;
    _observer;

    profile;
    isLoading = false;
    error;
    groupStates = [];
    evidence;
    evidenceLoading = false;
    evidenceError;
    expanded = {};
    isWide = false;

    /** { slug, text, mode, key } - a new object (new key) triggers a fresh load. */
    @api
    get request() {
        return this._request;
    }
    set request(value) {
        this._request = value;
        if (this._connected) {
            this.load();
        }
    }

    connectedCallback() {
        this._connected = true;
        if (this._request) {
            this.load();
        }
    }

    renderedCallback() {
        if (this._observer || typeof ResizeObserver === 'undefined') {
            return;
        }
        const root = this.refs.root;
        if (!root) {
            return;
        }
        this._observer = new ResizeObserver((entries) => {
            const width = entries.length ? entries[0].contentRect.width : 0;
            const wide = width >= WIDE_BREAKPOINT;
            if (wide !== this.isWide) {
                this.isWide = wide;
            }
        });
        this._observer.observe(root);
    }

    disconnectedCallback() {
        this._connected = false;
        if (this._observer) {
            this._observer.disconnect();
            this._observer = null;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Data loading
    // ---------------------------------------------------------------------------------------------

    async load() {
        const request = this._request;
        if (!request || !request.slug) {
            return;
        }
        const token = ++this._token;
        this.profile = undefined;
        this.error = undefined;
        this.groupStates = [];
        this.evidence = undefined;
        this.evidenceError = undefined;
        this.expanded = {};
        this.isLoading = true;

        let profile;
        try {
            profile = await getCancerProfile({ slug: request.slug });
        } catch (e) {
            if (token === this._token) {
                this.error = reduceError(e);
                this.isLoading = false;
            }
            return;
        }
        if (token !== this._token) {
            return;
        }
        this.profile = profile;
        this.isLoading = false;
        this.groupStates = (profile.groups || []).map((key) => ({ key, status: 'loading', sections: [] }));

        const tasks = (profile.groups || []).map((key) => this.loadGroup(token, key));
        if (request.text && request.text.trim()) {
            tasks.push(this.loadEvidence(token, request));
        }
        await Promise.all(tasks);
    }

    async loadGroup(token, key) {
        try {
            const sections = await getSectionGroup({
                slug: this.profile.slug,
                groupKey: key,
                availableCategories: this.profile.availableCategories
            });
            this.setGroup(token, key, { status: 'done', sections: sections || [], error: undefined });
        } catch (e) {
            this.setGroup(token, key, { status: 'error', sections: [], error: reduceError(e) });
        }
    }

    async loadEvidence(token, request) {
        this.evidenceLoading = true;
        try {
            const result = await findEvidence({
                slug: request.slug,
                inputText: request.text,
                mode: request.mode,
                availableCategories: this.profile.availableCategories
            });
            if (token === this._token) {
                this.evidence = result;
            }
        } catch (e) {
            if (token === this._token) {
                this.evidenceError = reduceError(e);
            }
        } finally {
            if (token === this._token) {
                this.evidenceLoading = false;
            }
        }
    }

    setGroup(token, key, patch) {
        if (token !== this._token) {
            return;
        }
        this.groupStates = this.groupStates.map((g) => (g.key === key ? { ...g, ...patch } : g));
    }

    handleRetry() {
        this.load();
    }

    handleRetryGroup(event) {
        const key = event.currentTarget.dataset.group;
        this.setGroup(this._token, key, { status: 'loading', error: undefined });
        this.loadGroup(this._token, key);
    }

    handleToggleSection(event) {
        const key = event.currentTarget.dataset.section;
        this.expanded = { ...this.expanded, [key]: !this.expanded[key] };
    }

    // ---------------------------------------------------------------------------------------------
    // View model
    // ---------------------------------------------------------------------------------------------

    get hasProfile() {
        return Boolean(this.profile);
    }

    get layoutClass() {
        return this.isWide ? 'ci-layout ci-layout_wide' : 'ci-layout';
    }

    get aliasText() {
        const aliases = (this.profile && this.profile.aliases) || [];
        return aliases.length ? aliases.join(', ') : null;
    }

    get hasHeaderMeta() {
        return Boolean(this.aliasText || (this.profile && this.profile.site));
    }

    get showMetaSeparator() {
        return Boolean(this.aliasText && this.profile && this.profile.site);
    }

    get codes() {
        return ((this.profile && this.profile.codes) || []).map((c) => ({ key: c.label, label: c.label, value: c.value }));
    }

    get hasCodes() {
        return this.codes.length > 0;
    }

    get matchedGroups() {
        return new Set((this.evidence && this.evidence.matchedGroups) || []);
    }

    get isClaim() {
        return Boolean(this._request && this._request.mode === 'claim');
    }

    get pendingCount() {
        return this.groupStates.filter((g) => g.status === 'loading').length + (this.evidenceLoading ? 1 : 0);
    }

    get isLoadingSections() {
        return this.pendingCount > 0;
    }

    get progressText() {
        const total = this.groupStates.length + (this.evidenceLoading || this.evidence || this.evidenceError ? 1 : 0);
        const done = total - this.pendingCount;
        return `Gathering sourced information… ${done} of ${total} sections ready`;
    }

    get failedGroups() {
        return this.groupStates
            .filter((g) => g.status === 'error')
            .map((g) => ({ key: g.key, title: (GROUP_META[g.key] || {}).title || g.key, error: g.error }));
    }

    get hasFailedGroups() {
        return this.failedGroups.length > 0;
    }

    buildCard(state) {
        const meta = GROUP_META[state.key] || { title: state.key, icon: 'utility:info', layout: 'bullets' };
        const multi = state.sections.length > 1;
        const sections = state.sections.map((section) => {
            const sectionKey = `${state.key}-${section.category}`;
            const isExpanded = Boolean(this.expanded[sectionKey]);
            const blocks = section.blocks || [];
            const limit = state.key === 'research' ? 2 : BLOCKS_PER_SECTION;
            const visible = isExpanded ? blocks : blocks.slice(0, limit);
            const hidden = blocks.length - limit;
            return {
                key: sectionKey,
                name: section.name,
                showName: multi,
                blocks: visible,
                canToggle: hidden > 0,
                toggleLabel: isExpanded ? 'Show fewer passages' : `Show ${hidden} more passage${hidden === 1 ? '' : 's'}`
            };
        });
        const matched = this.matchedGroups.has(state.key);
        let cardClass = 'ci-card';
        if (meta.boxed) {
            cardClass += ' ci-card_boxed';
        }
        if (matched) {
            cardClass += ' ci-card_matched';
        }
        return {
            key: state.key,
            title: meta.title,
            subtitle: meta.subtitle,
            icon: meta.icon,
            note: meta.note,
            layout: meta.layout,
            sections,
            matched,
            matchedLabel: this.isClaim ? 'Related to your claim' : 'Related to your question',
            cardClass
        };
    }

    get mainCards() {
        const cards = [];
        const overviewState = this.groupStates.find((g) => g.key === 'overview');
        const overviewHasData = overviewState && overviewState.status === 'done' && overviewState.sections.length > 0;
        if (this.profile && this.profile.description && !overviewHasData) {
            const overviewLoading = overviewState && overviewState.status === 'loading';
            if (!overviewLoading) {
                cards.push(
                    this.buildCard({
                        key: 'overview',
                        sections: [
                            {
                                category: 'description',
                                name: 'Overview',
                                blocks: [
                                    {
                                        id: 'profile-description',
                                        parts: [{ key: 'p0', isList: false, text: this.profile.description }],
                                        sources: []
                                    }
                                ]
                            }
                        ]
                    })
                );
            }
        }
        this.groupStates.forEach((state) => {
            if (state.key !== 'research' && state.status === 'done' && state.sections.length > 0) {
                cards.push(this.buildCard(state));
            }
        });
        return cards;
    }

    get researchCard() {
        const state = this.groupStates.find((g) => g.key === 'research');
        return state && state.status === 'done' && state.sections.length > 0 ? this.buildCard(state) : null;
    }

    get sources() {
        const seen = new Map();
        const add = (s) => {
            if (!s) {
                return;
            }
            const href = safeHref(s.url);
            const key = href || `${s.organization}|${s.title}`;
            if (!seen.has(key)) {
                seen.set(key, {
                    key,
                    organization: s.organization || 'Source',
                    title: s.title,
                    href,
                    updated: s.updated,
                    attribution: s.attribution
                });
            }
        };
        this.groupStates.forEach((g) =>
            (g.sections || []).forEach((sec) => (sec.blocks || []).forEach((b) => (b.sources || []).forEach(add)))
        );
        ((this.evidence && this.evidence.items) || []).forEach((item) => (item.sources || []).forEach(add));
        return Array.from(seen.values());
    }

    get visibleSources() {
        return this.sources.slice(0, MAX_SOURCES);
    }

    get hasSources() {
        return this.sources.length > 0;
    }

    get extraSourceCount() {
        return Math.max(0, this.sources.length - MAX_SOURCES);
    }

    get relatedTools() {
        const name = (this.profile && this.profile.name) || '';
        return [
            {
                key: 'trials',
                label: 'Explore Clinical Trials',
                caption: 'ClinicalTrials.gov',
                href: `https://clinicaltrials.gov/search?cond=${encodeURIComponent(name)}`
            },
            {
                key: 'support',
                label: 'Find Support Resources',
                caption: 'National Cancer Institute',
                href: 'https://www.cancer.gov/about-cancer/coping'
            }
        ];
    }

    get evidenceCard() {
        const ev = this.evidence;
        if (!ev || !ev.items || ev.items.length === 0) {
            return null;
        }
        return {
            title: this.isClaim ? 'What Trusted Sources Say About This Claim' : 'Passages Related to Your Question',
            icon: this.isClaim ? 'utility:quotation_marks' : 'utility:question',
            items: ev.items.map((item, index) => {
                const source = (item.sources || [])[0] || {};
                return {
                    key: `${item.key}-${index}`,
                    categoryName: item.categoryName,
                    excerpt: item.excerpt,
                    region: item.region,
                    organization: source.organization,
                    href: safeHref(source.url)
                };
            })
        };
    }

    get askedText() {
        return this._request ? this._request.text : '';
    }

    get evidenceNotice() {
        if (this.evidenceError) {
            return `We couldn't search for related passages: ${this.evidenceError}`;
        }
        const ev = this.evidence;
        if (!ev || (ev.items && ev.items.length > 0)) {
            return null;
        }
        if (!ev.keywords || ev.keywords.length === 0) {
            return 'Try adding a topic word such as “symptoms”, “treatment” or “screening” to find specific passages. The full profile is shown below.';
        }
        if (ev.matchedGroups && ev.matchedGroups.length) {
            return 'No passage matched your exact words. The highlighted sections below cover the related topics.';
        }
        return 'No passages matched your words for this cancer yet. The full profile is shown below.';
    }

    get showClaimNote() {
        return this.isClaim && Boolean(this.evidenceCard || this.evidenceNotice);
    }

    get noDetailedData() {
        return Boolean(this.profile) && (this.profile.groups || []).length === 0;
    }

    get disclaimer() {
        return (
            (this.profile && this.profile.disclaimer) ||
            'CancerInfo API provides public informational data. It does not provide medical diagnosis or personal treatment recommendations.'
        );
    }
}
