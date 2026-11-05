/**
 * Shared, framework-free helpers for the CancerInfo Explorer components.
 * Kept pure so they can be unit tested with plain Node / Jest.
 */

export const MAX_SUGGESTIONS = 8;

const IGNORED_TOKENS = new Set([
    'a', 'an', 'the', 'is', 'are', 'of', 'in', 'on', 'to', 'for', 'and', 'or', 'it', 'its', 'can', 'do', 'does',
    'what', 'how', 'which', 'who', 'my', 'i', 'be', 'by', 'with', 'about', 'that', 'this'
]);

/**
 * Turns any LDS / Apex / JS error into a readable message.
 */
export function reduceError(error) {
    if (!error) {
        return 'Something went wrong. Please try again.';
    }
    if (Array.isArray(error.body)) {
        return error.body.map((e) => e.message).filter(Boolean).join(', ');
    }
    if (error.body && typeof error.body.message === 'string' && error.body.message) {
        return error.body.message;
    }
    if (typeof error.message === 'string' && error.message) {
        return error.message;
    }
    return 'Something went wrong. Please try again.';
}

export function tokenize(text) {
    return (text || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .split(/[^a-z0-9]+/)
        .filter((t) => t.length > 0);
}

/**
 * Filters and ranks type-ahead options.
 * @param {Array<{value:string,label:string,keywords?:string[]}>} options
 * @param {string} text   what the user typed
 * @param {'all'|'any'} mode  'all' = every typed word must match (cancer names); 'any' = rank by overlap (questions)
 * @param {boolean} showAllWhenEmpty  list everything when nothing is typed
 */
export function filterOptions(options, text, mode = 'all', showAllWhenEmpty = false, limit = MAX_SUGGESTIONS) {
    const list = Array.isArray(options) ? options : [];
    let tokens = tokenize(text);
    if (mode === 'any') {
        tokens = tokens.filter((t) => !IGNORED_TOKENS.has(t));
    }
    if (tokens.length === 0) {
        return showAllWhenEmpty ? list.slice(0, limit) : [];
    }
    const typed = (text || '').trim().toLowerCase();
    const scored = [];
    list.forEach((option, index) => {
        const words = tokenize([option.label, ...(option.keywords || [])].join(' '));
        let hits = 0;
        tokens.forEach((token) => {
            if (words.some((w) => w.startsWith(token) || (token.length >= 4 && w.includes(token)))) {
                hits++;
            }
        });
        const passes = mode === 'all' ? hits === tokens.length : hits > 0;
        if (!passes) {
            return;
        }
        const label = (option.label || '').toLowerCase();
        let score = hits * 10;
        if (label === typed) {
            score += 100;
        } else if (label.startsWith(typed)) {
            score += 50;
        }
        scored.push({ option, score, index });
    });
    scored.sort((a, b) => b.score - a.score || a.index - b.index);
    return scored.slice(0, limit).map((s) => s.option);
}

/**
 * Resolves free text to a cancer option: exact name / alias / slug first, then a single unambiguous match.
 */
export function resolveCancer(cancers, text) {
    const list = Array.isArray(cancers) ? cancers : [];
    const typed = (text || '').trim().toLowerCase();
    if (!typed) {
        return null;
    }
    const exact = list.find(
        (c) =>
            (c.name || '').toLowerCase() === typed ||
            (c.slug || '').toLowerCase() === typed ||
            (c.aliases || []).some((a) => (a || '').toLowerCase() === typed)
    );
    if (exact) {
        return exact;
    }
    const options = list.map((c) => ({ value: c.slug, label: c.name, keywords: c.aliases || [] }));
    const matches = filterOptions(options, typed, 'all', false, 2);
    return matches.length === 1 ? list.find((c) => c.slug === matches[0].value) : null;
}

const QUESTION_TEMPLATES = [
    { category: 'overview', text: 'What is {name}?' },
    { category: 'types_and_subtypes', text: 'What are the different types of {name}?' },
    { category: 'symptoms', text: 'What are the common symptoms of {name}?' },
    { category: 'signs', text: 'What signs of {name} can a doctor find?' },
    { category: 'early_detection', text: 'What are the early warning signs of {name}?' },
    { category: 'causes', text: 'What causes {name}?' },
    { category: 'risk_factors', text: 'What are the risk factors for {name}?' },
    { category: 'genetics', text: 'Is {name} hereditary or linked to genes like BRCA?' },
    { category: 'prevention', text: 'Can the risk of {name} be reduced?' },
    { category: 'screening', text: 'Who should be screened for {name}, and how?' },
    { category: 'diagnosis', text: 'How is {name} diagnosed?' },
    { category: 'diagnostic_tests', text: 'Which tests and scans are used to diagnose {name}?' },
    { category: 'staging', text: 'How is {name} staged?' },
    { category: 'grading', text: 'What does the grade of {name} mean?' },
    { category: 'biomarkers', text: 'Which biomarkers are tested in {name}?' },
    { category: 'treatment', text: 'How is {name} usually treated?' },
    { category: 'surgery', text: 'What types of surgery are used for {name}?' },
    { category: 'chemotherapy', text: 'When is chemotherapy used for {name}?' },
    { category: 'radiation_therapy', text: 'How is radiation therapy used for {name}?' },
    { category: 'immunotherapy', text: 'Is immunotherapy used for {name}?' },
    { category: 'targeted_therapy', text: 'What targeted therapies exist for {name}?' },
    { category: 'hormone_therapy', text: 'How does hormone therapy work for {name}?' },
    { category: 'side_effects', text: 'What are common side effects of {name} treatment?' },
    { category: 'recurrence', text: 'Can {name} come back after treatment?' },
    { category: 'follow_up', text: 'What follow-up care is needed after {name} treatment?' },
    { category: 'prognosis', text: 'What is the outlook for people with {name}?' },
    { category: 'survival', text: 'What are the survival rates for {name}?' },
    { category: 'statistics', text: 'How common is {name}?' },
    { category: 'living_with_cancer', text: 'What support is available for living with {name}?' },
    { category: 'clinical_trials', text: 'Are there clinical trials for {name}?' },
    { category: 'research', text: 'What new research is being done on {name}?' }
];

const CLAIM_TEMPLATES = [
    { category: 'symptoms', text: 'A painless lump is never a sign of {name}.' },
    { category: 'symptoms', text: '{name} always causes symptoms early on.' },
    { category: 'screening', text: 'Regular screening helps find {name} early.' },
    { category: 'causes', text: '{name} is caused only by inherited genes.' },
    { category: 'risk_factors', text: 'Only older people get {name}.' },
    { category: 'genetics', text: 'Everyone with a BRCA change will develop {name}.' },
    { category: 'prevention', text: '{name} cannot be prevented at all.' },
    { category: 'treatment', text: 'Surgery is the only treatment for {name}.' },
    { category: 'chemotherapy', text: 'Chemotherapy is always needed for {name}.' },
    { category: 'diagnosis', text: 'A blood test alone can diagnose {name}.' },
    { category: 'prognosis', text: '{name} is always fatal.' },
    { category: 'recurrence', text: '{name} never comes back after treatment.' },
    { category: 'overview', text: '{name} is contagious.' }
];

/**
 * Builds type-ahead suggestions for the question / claim box, limited to topics the
 * selected cancer actually has data for (falls back to generic wording when none is selected).
 */
export function buildPromptSuggestions(cancer, mode) {
    const isClaim = mode === 'claim';
    const templates = isClaim ? CLAIM_TEMPLATES : QUESTION_TEMPLATES;
    const name = cancer && cancer.name ? cancer.name : 'this cancer';
    const available = cancer && Array.isArray(cancer.categories) && cancer.categories.length ? new Set(cancer.categories) : null;
    const chosen = templates.filter((t) => !available || available.has(t.category) || t.category === 'overview');
    const seen = new Set();
    return chosen
        .map((t, index) => {
            let text = t.text.replace('{name}', name);
            text = text.charAt(0).toUpperCase() + text.slice(1);
            return {
                value: `${isClaim ? 'claim' : 'q'}-${index}`,
                label: text,
                meta: available && available.has(t.category) ? `Topic: ${categoryLabel(t.category)}` : 'General',
                keywords: [t.category.replace(/_/g, ' ')],
                icon: isClaim ? 'utility:quote' : 'utility:question'
            };
        })
        .filter((s) => {
            if (seen.has(s.label)) {
                return false;
            }
            seen.add(s.label);
            return true;
        });
}

export function categoryLabel(category) {
    return (category || '')
        .split('_')
        .map((w) => (w === 'and' ? '&' : w.charAt(0).toUpperCase() + w.slice(1)))
        .join(' ');
}

/** Builds the display text under a cancer option in the type-ahead. */
export function cancerMeta(cancer) {
    const parts = [];
    if (cancer.site) {
        parts.push(cancer.site);
    }
    const topics = (cancer.categories || []).length;
    parts.push(topics > 0 ? `${topics} topic${topics === 1 ? '' : 's'} available` : 'Basic profile only');
    return parts.join(' · ');
}

/** Only allows http(s) links in templates. */
export function safeHref(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url.trim()) ? url.trim() : null;
}
