/**
 * @description Lightning controller for the CancerInfo Explorer components.
 *              Calls the public CancerInfo API (read-only, retrieval only - no AI) and reshapes
 *              its records into display-ready sections. Educational information only; not medical advice.
 */
public with sharing class CancerInfoController {
    // ---------------------------------------------------------------------------------------------
    // Constants
    // ---------------------------------------------------------------------------------------------
    private static final Pattern SLUG_PATTERN = Pattern.compile('^[a-z0-9][a-z0-9-]{0,79}$');
    private static final Pattern CATEGORY_PATTERN = Pattern.compile('^[a-z_]{1,60}$');
    private static final String SENTENCE_SPLIT = '(?<=[.!?])\\s+(?=[A-Z])';
    private static final Pattern INLINE_LIST = Pattern.compile('^(.{0,160}?\\b(?:include|includes|including)\\b:?)\\s+(.+?)\\.?$');

    @TestVisible
    private static final Integer MAX_INPUT_LENGTH = 500;
    @TestVisible
    private static final Integer MAX_CONTENT_LENGTH = 2500;
    private static final Integer RECORDS_PER_CATEGORY = 10;
    private static final Integer MAX_EVIDENCE_ITEMS = 5;
    private static final Integer MAX_EVIDENCE_CATEGORIES = 5;
    private static final Integer MAX_KEYWORDS = 8;

    /** Display groups, in on-screen order. Each group becomes one card when it has data. */
    @TestVisible
    private static final List<String> GROUP_ORDER = new List<String>{
        'overview',
        'treatment',
        'symptoms',
        'diagnosis',
        'causes',
        'living',
        'outlook',
        'research'
    };

    /** Canonical CancerInfo API categories that feed each display group (ordered). */
    @TestVisible
    private static final Map<String, List<String>> GROUP_CATEGORIES = new Map<String, List<String>>{
        'overview' => new List<String>{ 'overview', 'types_and_subtypes', 'terminology' },
        'treatment' => new List<String>{
            'treatment',
            'surgery',
            'chemotherapy',
            'radiation_therapy',
            'immunotherapy',
            'targeted_therapy',
            'hormone_therapy',
            'stem_cell_transplant'
        },
        'symptoms' => new List<String>{ 'symptoms', 'signs', 'early_detection' },
        'diagnosis' => new List<String>{
            'screening',
            'diagnosis',
            'diagnostic_tests',
            'biomarkers',
            'grading',
            'staging'
        },
        'causes' => new List<String>{ 'causes', 'risk_factors', 'genetics', 'prevention' },
        'living' => new List<String>{
            'side_effects',
            'supportive_care',
            'follow_up',
            'recurrence',
            'palliative_care',
            'living_with_cancer',
            'caregiver_information',
            'childhood_cancer'
        },
        'outlook' => new List<String>{ 'prognosis', 'survival', 'statistics' },
        'research' => new List<String>{ 'research', 'clinical_trials' }
    };

    private static final Set<String> STOPWORDS = new Set<String>(
        ('a an the is are was were be been being am do does did done can could should would will may might must shall ' +
            'what which who whom whose when where how of in on at to for from by with about as into onto than then that ' +
            'this these those it its i me my mine we us our you your he him his she her they them their and or but if so ' +
            'not no yes there here any all some more most less very really just also only true false claim claims heard ' +
            'hear read say says said tell know get gets getting got have has had people someone anyone person persons ' +
            'cancer cancers tumor tumour tumors tumours disease always never everyone nobody thing things way ways like')
            .split(' ')
    );

    private static final Map<String, List<String>> KEYWORD_CATEGORIES = buildKeywordMap();

    // ---------------------------------------------------------------------------------------------
    // Aura-enabled API
    // ---------------------------------------------------------------------------------------------

    /**
     * @description Predefined cancer list for the type-ahead (live from GET /v1/cancers, enriched
     *              with GET /v1/coverage so the UI can show how many topics each cancer has).
     */
    @AuraEnabled(cacheable=true)
    public static List<CancerOption> getCancers() {
        Map<String, Object> body;
        try {
            body = CancerInfoApiClient.get('/v1/cancers', new Map<String, String>{ 'limit' => '50' });
        } catch (CancerInfoApiClient.CancerInfoApiException e) {
            throw auraError(e.getMessage());
        }

        Map<String, Map<String, Object>> coverage = loadCoverage();
        List<CancerOption> options = new List<CancerOption>();
        for (Object item : asList(body.get('data'))) {
            Map<String, Object> row = asMap(item);
            String slug = asString(row.get('slug'));
            if (String.isBlank(slug) || !SLUG_PATTERN.matcher(slug).matches()) {
                continue;
            }
            CancerOption option = new CancerOption();
            option.slug = slug;
            option.name = asString(row.get('canonical_name'));
            option.site = asString(row.get('anatomical_site'));
            option.aliases = readAliases(row.get('aliases'));
            option.categories = new List<String>();
            option.recordCount = 0;
            Map<String, Object> cov = coverage.get(slug);
            if (cov != null) {
                option.categories = asStringList(cov.get('categories_covered'));
                option.recordCount = asInteger(cov.get('total_records'));
            }
            options.add(option);
        }
        options.sort();
        return options;
    }

    /**
     * @description Header data for the result card plus the list of display groups that have data.
     */
    @AuraEnabled(cacheable=true)
    public static CancerProfile getCancerProfile(String slug) {
        validateSlug(slug);
        Map<String, Object> body;
        try {
            body = CancerInfoApiClient.get('/v1/cancers/' + slug, null);
        } catch (CancerInfoApiClient.CancerInfoApiException e) {
            throw auraError(e.getMessage());
        }
        Map<String, Object> data = asMap(body.get('data'));
        Map<String, Object> meta = asMap(body.get('meta'));

        CancerProfile profile = new CancerProfile();
        profile.slug = slug;
        profile.name = asString(data.get('canonical_name'));
        profile.description = asString(data.get('description'));
        profile.site = asString(data.get('anatomical_site'));
        profile.aliases = readAliases(data.get('aliases'));
        profile.disclaimer = asString(meta.get('disclaimer'));
        profile.codes = new List<LabelValue>();
        Map<String, Object> codes = asMap(data.get('taxonomy_codes'));
        List<String> codeKeys = new List<String>(codes.keySet());
        codeKeys.sort();
        for (String key : codeKeys) {
            String value = asString(codes.get(key));
            if (String.isNotBlank(value)) {
                profile.codes.add(new LabelValue(key, value));
            }
        }
        profile.availableCategories = asStringList(data.get('available_categories'));
        profile.groups = groupsFor(profile.availableCategories);
        return profile;
    }

    /**
     * @description Loads every available category of one display group and returns parsed sections.
     *              Categories that return no records are omitted, so empty cards never render.
     */
    @AuraEnabled(cacheable=true)
    public static List<Section> getSectionGroup(String slug, String groupKey, List<String> availableCategories) {
        validateSlug(slug);
        if (String.isBlank(groupKey) || !GROUP_CATEGORIES.containsKey(groupKey)) {
            throw auraError('Unknown section requested.');
        }
        Set<String> available = new Set<String>(availableCategories == null ? new List<String>() : availableCategories);

        List<Section> sections = new List<Section>();
        String firstError;
        for (String category : GROUP_CATEGORIES.get(groupKey)) {
            if (!available.contains(category)) {
                continue;
            }
            try {
                Section section = loadSection(slug, category);
                if (section != null) {
                    sections.add(section);
                }
            } catch (CancerInfoApiClient.CancerInfoApiException e) {
                if (e.statusCode != 404 && firstError == null) {
                    firstError = e.getMessage();
                }
            }
        }
        if (sections.isEmpty() && firstError != null) {
            throw auraError(firstError);
        }
        return sections;
    }

    /**
     * @description Finds passages related to a typed question or claim for one cancer.
     *              Retrieval only: passages are ranked by keyword overlap; no verdict is produced.
     * @param mode 'question' or 'claim'
     */
    @AuraEnabled(cacheable=true)
    public static Evidence findEvidence(String slug, String inputText, String mode, List<String> availableCategories) {
        validateSlug(slug);
        String text = inputText == null ? '' : inputText.normalizeSpace();
        if (String.isBlank(text)) {
            throw auraError('Please type a question or a claim.');
        }
        if (text.length() > MAX_INPUT_LENGTH) {
            throw auraError('Please keep your text under ' + MAX_INPUT_LENGTH + ' characters.');
        }

        Evidence result = new Evidence();
        result.mode = 'claim'.equalsIgnoreCase(mode) ? 'claim' : 'question';
        result.keywords = extractKeywords(text, slug);
        result.matchedCategories = new List<String>();
        result.matchedGroups = new List<String>();
        result.items = new List<EvidenceItem>();

        Set<String> available = new Set<String>(availableCategories == null ? new List<String>() : availableCategories);
        for (String category : matchCategories(result.keywords)) {
            if (available.contains(category)) {
                result.matchedCategories.add(category);
            }
        }
        Set<String> groupSet = new Set<String>();
        for (String category : result.matchedCategories) {
            groupSet.add(groupOf(category));
        }
        for (String groupKey : GROUP_ORDER) {
            if (groupSet.contains(groupKey)) {
                result.matchedGroups.add(groupKey);
            }
        }
        if (result.keywords.isEmpty()) {
            return result;
        }

        List<ScoredItem> scored = new List<ScoredItem>();
        Set<String> seen = new Set<String>();

        // 1) Records from the categories the question maps to.
        Integer fetched = 0;
        for (String category : result.matchedCategories) {
            if (fetched >= MAX_EVIDENCE_CATEGORIES) {
                break;
            }
            fetched++;
            Map<String, Object> data;
            try {
                data = asMap(CancerInfoApiClient.get('/v1/cancers/' + slug + '/' + category, categoryQuery()).get('data'));
            } catch (CancerInfoApiClient.CancerInfoApiException e) {
                continue;
            }
            for (Object rec : asList(data.get('records'))) {
                addScored(scored, seen, asMap(rec), category, result.keywords, 1);
            }
        }

        // 2) Full-text search across the API, filtered to the selected cancer.
        try {
            List<String> terms = new List<String>(result.keywords);
            for (String word : slug.split('-')) {
                if (!STOPWORDS.contains(word)) {
                    terms.add(word); // biases ranking toward the selected cancer
                }
            }
            Map<String, Object> body = CancerInfoApiClient.get(
                '/v1/search',
                new Map<String, String>{ 'q' => String.join(terms, ' '), 'limit' => '50' }
            );
            for (Object hit : asList(asMap(body.get('data')).get('results'))) {
                Map<String, Object> row = asMap(hit);
                if (asString(row.get('match_type')) != 'content_record') {
                    continue;
                }
                if (asString(asMap(row.get('cancer')).get('slug')) != slug) {
                    continue;
                }
                Map<String, Object> rec = asMap(row.get('record'));
                if (rec.isEmpty()) {
                    continue;
                }
                String category = asString(row.get('category'));
                if (String.isBlank(category)) {
                    category = asString(rec.get('category'));
                }
                addScored(scored, seen, rec, category, result.keywords, 0);
            }
        } catch (CancerInfoApiClient.CancerInfoApiException e) {
            // Search is a best-effort enrichment; category matches above are still returned.
            System.debug(LoggingLevel.FINE, 'CancerInfo search skipped: ' + e.getMessage());
        }

        scored.sort();
        for (ScoredItem s : scored) {
            if (result.items.size() >= MAX_EVIDENCE_ITEMS) {
                break;
            }
            if (s.score <= 0) {
                continue;
            }
            result.items.add(s.item);
        }
        return result;
    }

    // ---------------------------------------------------------------------------------------------
    // Section loading and content parsing
    // ---------------------------------------------------------------------------------------------

    private static Map<String, String> categoryQuery() {
        return new Map<String, String>{ 'language' => 'en', 'limit' => String.valueOf(RECORDS_PER_CATEGORY) };
    }

    @TestVisible
    private static Section loadSection(String slug, String category) {
        if (!CATEGORY_PATTERN.matcher(category).matches()) {
            return null;
        }
        Map<String, Object> data = asMap(
            CancerInfoApiClient.get('/v1/cancers/' + slug + '/' + category, categoryQuery()).get('data')
        );
        Section section = new Section();
        section.category = category;
        section.groupKey = groupOf(category);
        section.name = String.isNotBlank(asString(data.get('category_name')))
            ? asString(data.get('category_name'))
            : categoryLabel(category);
        section.blocks = new List<ContentBlock>();

        Set<String> seenContent = new Set<String>();
        String consensus = asString(data.get('consensus_summary'));
        if (String.isNotBlank(consensus)) {
            ContentBlock block = buildBlock(category + '-consensus', consensus, null, new List<SourceRef>());
            block.isConsensus = true;
            section.blocks.add(block);
            seenContent.add(consensus.normalizeSpace().toLowerCase());
        }

        for (Object rec : asList(data.get('records'))) {
            Map<String, Object> record = asMap(rec);
            String content = asString(record.get('content'));
            if (String.isBlank(content)) {
                continue;
            }
            String fingerprint = content.normalizeSpace().toLowerCase();
            if (seenContent.contains(fingerprint)) {
                continue;
            }
            seenContent.add(fingerprint);
            section.blocks.add(
                buildBlock(
                    asString(record.get('id')),
                    content,
                    regionLabel(asMap(record.get('jurisdiction'))),
                    readSources(record.get('sources'))
                )
            );
        }
        return section.blocks.isEmpty() ? null : section;
    }

    @TestVisible
    private static ContentBlock buildBlock(String id, String content, String region, List<SourceRef> sources) {
        ContentBlock block = new ContentBlock();
        block.id = String.isBlank(id) ? String.valueOf(Crypto.getRandomInteger()) : id;
        block.region = region;
        block.sources = sources;
        block.isConsensus = false;
        block.truncated = false;

        String text = content;
        if (text.length() > MAX_CONTENT_LENGTH) {
            text = text.substring(0, MAX_CONTENT_LENGTH);
            Integer lastBreak = Math.max(text.lastIndexOf('\n'), text.lastIndexOf('. '));
            if (lastBreak > MAX_CONTENT_LENGTH / 2) {
                text = text.substring(0, lastBreak + 1);
            }
            block.truncated = true;
        }

        List<String> lines = new List<String>();
        for (String line : text.replace('\r\n', '\n').replace('\r', '\n').split('\n')) {
            // Source text sometimes carries stray spaces around punctuation ("chemotherapy , with").
            String clean = line.normalizeSpace().replace(' ,', ',').replace(' .', '.').replace('( ', '(').replace(' )', ')');
            if (String.isNotBlank(clean)) {
                lines.add(clean);
            }
        }
        if (lines.size() > 1 && isHeadingLine(lines[0])) {
            block.heading = lines.remove(0);
        }
        block.parts = lines.size() == 1 ? parseSingleParagraph(lines[0]) : parseLines(lines);
        return block;
    }

    /** Multi-line content: short un-punctuated lines become bullets, the rest paragraphs. */
    @TestVisible
    private static List<ContentPart> parseLines(List<String> lines) {
        List<ContentPart> parts = new List<ContentPart>();
        ContentPart currentList;
        // True when a list was introduced by "...:" and its items are full sentences ending in "."
        // (NCI style); following sentence-like lines then continue the same list.
        Boolean sentenceList = false;
        for (Integer i = 0; i < lines.size(); i++) {
            String line = lines[i];
            Boolean afterColon = i > 0 && lines[i - 1].endsWith(':');
            Boolean continuesList = currentList != null && sentenceList && line.endsWith('.');
            Boolean bullet = line.length() <= 220 && (afterColon || continuesList || !endsWithPunctuation(line));
            if (line.endsWith(':') || line.endsWith('?')) {
                bullet = false;
            }
            if (bullet) {
                if (currentList == null) {
                    currentList = newListPart(parts.size());
                    sentenceList = afterColon && line.endsWith('.');
                    parts.add(currentList);
                }
                currentList.items.add(capitalize(stripListPrefix(line)));
            } else {
                currentList = null;
                sentenceList = false;
                parts.add(newTextPart(parts.size(), line));
            }
        }
        // A lone "bullet" that is not introduced by a colon is really a sub-heading.
        for (Integer i = 0; i < parts.size(); i++) {
            ContentPart part = parts[i];
            Boolean introduced = i > 0 && !parts[i - 1].isList && parts[i - 1].text.endsWith(':');
            if (part.isList && part.items.size() == 1 && !introduced && i < parts.size() - 1) {
                ContentPart sub = newTextPart(i, part.items[0]);
                sub.isSubheading = true;
                parts[i] = sub;
            }
        }
        return parts;
    }

    /** Single paragraph: pull an inline "X include a, b, and c" enumeration out into bullets. */
    @TestVisible
    private static List<ContentPart> parseSingleParagraph(String paragraph) {
        List<ContentPart> parts = new List<ContentPart>();
        List<String> sentences = paragraph.split(SENTENCE_SPLIT);
        List<String> pending = new List<String>();
        for (String sentence : sentences) {
            Matcher m = INLINE_LIST.matcher(sentence);
            List<String> items = m.matches() ? splitTopLevel(m.group(2)) : new List<String>();
            if (items.size() >= 3) {
                if (!pending.isEmpty()) {
                    parts.add(newTextPart(parts.size(), String.join(pending, ' ')));
                    pending.clear();
                }
                ContentPart intro = newTextPart(parts.size(), m.group(1).removeEnd(':') + ':');
                intro.isIntro = true;
                parts.add(intro);
                ContentPart listPart = newListPart(parts.size());
                for (String item : items) {
                    listPart.items.add(capitalize(item));
                }
                parts.add(listPart);
            } else {
                pending.add(sentence);
            }
        }
        if (!pending.isEmpty()) {
            parts.add(newTextPart(parts.size(), String.join(pending, ' ')));
        }
        return parts;
    }

    /** Splits "a, b (x, y), and c" on top-level commas, dropping a leading "and"/"or". */
    @TestVisible
    private static List<String> splitTopLevel(String text) {
        List<String> items = new List<String>();
        Integer depth = 0;
        Integer start = 0;
        for (Integer i = 0; i < text.length(); i++) {
            String ch = text.substring(i, i + 1);
            if (ch == '(' || ch == '[') {
                depth++;
            } else if ((ch == ')' || ch == ']') && depth > 0) {
                depth--;
            } else if ((ch == ',' || ch == ';') && depth == 0) {
                items.add(text.substring(start, i));
                start = i + 1;
            }
        }
        items.add(text.substring(start));

        List<String> cleaned = new List<String>();
        for (String raw : items) {
            String item = raw.normalizeSpace();
            item = item.removeStartIgnoreCase('and ').removeStartIgnoreCase('or ').trim();
            item = item.removeEnd('.').trim();
            if (String.isNotBlank(item)) {
                cleaned.add(item);
            }
        }
        // "a, b and c" (no Oxford comma) -> split the last item on " and ".
        if (cleaned.size() >= 2) {
            String last = cleaned[cleaned.size() - 1];
            Integer andIdx = last.lastIndexOf(' and ');
            if (andIdx > 0 && !last.contains('(')) {
                cleaned[cleaned.size() - 1] = last.substring(0, andIdx).trim();
                cleaned.add(last.substring(andIdx + 5).trim());
            }
        }
        return cleaned;
    }

    // ---------------------------------------------------------------------------------------------
    // Question / claim matching
    // ---------------------------------------------------------------------------------------------

    @TestVisible
    private static List<String> extractKeywords(String text, String slug) {
        Set<String> exclude = new Set<String>(STOPWORDS);
        exclude.addAll(slug.split('-'));
        List<String> keywords = new List<String>();
        Set<String> seen = new Set<String>();
        for (String token : text.toLowerCase().replaceAll('[^a-z0-9\\- ]', ' ').split(' ')) {
            String t = token.removeStart('-').removeEnd('-');
            if (t.length() < 2 || exclude.contains(t) || seen.contains(t)) {
                continue;
            }
            seen.add(t);
            keywords.add(t);
            if (keywords.size() >= MAX_KEYWORDS) {
                break;
            }
        }
        return keywords;
    }

    @TestVisible
    private static List<String> matchCategories(List<String> keywords) {
        List<String> ordered = new List<String>();
        Set<String> seen = new Set<String>();
        for (String keyword : keywords) {
            List<String> cats = KEYWORD_CATEGORIES.get(keyword);
            if (cats == null && keyword.endsWith('s')) {
                cats = KEYWORD_CATEGORIES.get(keyword.removeEnd('s'));
            }
            if (cats == null) {
                continue;
            }
            for (String category : cats) {
                if (!seen.contains(category)) {
                    seen.add(category);
                    ordered.add(category);
                }
            }
        }
        return ordered;
    }

    private static void addScored(
        List<ScoredItem> scored,
        Set<String> seen,
        Map<String, Object> record,
        String category,
        List<String> keywords,
        Integer bonus
    ) {
        String content = asString(record.get('content'));
        if (String.isBlank(content)) {
            return;
        }
        String fingerprint = content.normalizeSpace().toLowerCase();
        String key = String.isNotBlank(asString(record.get('id'))) ? asString(record.get('id')) : fingerprint;
        if (seen.contains(key) || seen.contains(fingerprint)) {
            return;
        }
        seen.add(key);
        seen.add(fingerprint);

        String lower = content.toLowerCase();
        Integer hits = 0;
        for (String keyword : keywords) {
            if (lower.contains(keyword)) {
                hits++;
            }
        }
        EvidenceItem item = new EvidenceItem();
        item.key = key.length() > 80 ? key.substring(0, 80) : key;
        item.category = category;
        item.categoryName = categoryLabel(category);
        item.groupKey = groupOf(category);
        item.excerpt = bestExcerpt(content, keywords);
        item.region = regionLabel(asMap(record.get('jurisdiction')));
        item.sources = readSources(record.get('sources'));
        scored.add(new ScoredItem(item, hits * 2 + (hits > 0 ? bonus : 0)));
    }

    /** Up to two sentences that mention a keyword; otherwise the opening of the passage. */
    @TestVisible
    private static String bestExcerpt(String content, List<String> keywords) {
        String flat = content.replace('\n', ' ').normalizeSpace();
        List<String> picked = new List<String>();
        for (String sentence : flat.split(SENTENCE_SPLIT)) {
            String lower = sentence.toLowerCase();
            for (String keyword : keywords) {
                if (lower.contains(keyword)) {
                    picked.add(sentence);
                    break;
                }
            }
            if (picked.size() == 2) {
                break;
            }
        }
        String excerpt = picked.isEmpty() ? flat : String.join(picked, ' ');
        return excerpt.length() > 420 ? excerpt.substring(0, 417).trim() + '...' : excerpt;
    }

    // ---------------------------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------------------------

    private static Map<String, Map<String, Object>> loadCoverage() {
        Map<String, Map<String, Object>> bySlug = new Map<String, Map<String, Object>>();
        try {
            Map<String, Object> body = CancerInfoApiClient.get('/v1/coverage', null);
            for (Object item : asList(asMap(body.get('data')).get('cancers'))) {
                Map<String, Object> row = asMap(item);
                String slug = asString(row.get('slug'));
                if (String.isNotBlank(slug)) {
                    bySlug.put(slug, row);
                }
            }
        } catch (CancerInfoApiClient.CancerInfoApiException e) {
            // Coverage only enriches the list (topic counts); the list still works without it.
            System.debug(LoggingLevel.FINE, 'CancerInfo coverage skipped: ' + e.getMessage());
        }
        return bySlug;
    }

    @TestVisible
    private static List<String> groupsFor(List<String> availableCategories) {
        Set<String> available = new Set<String>(availableCategories);
        List<String> groups = new List<String>();
        for (String groupKey : GROUP_ORDER) {
            for (String category : GROUP_CATEGORIES.get(groupKey)) {
                if (available.contains(category)) {
                    groups.add(groupKey);
                    break;
                }
            }
        }
        return groups;
    }

    @TestVisible
    private static String groupOf(String category) {
        for (String groupKey : GROUP_ORDER) {
            if (GROUP_CATEGORIES.get(groupKey).contains(category)) {
                return groupKey;
            }
        }
        return 'overview';
    }

    @TestVisible
    private static String categoryLabel(String category) {
        if (String.isBlank(category)) {
            return 'General';
        }
        List<String> words = new List<String>();
        for (String word : category.split('_')) {
            words.add(word == 'and' ? '&' : word.capitalize());
        }
        return String.join(words, ' ');
    }

    private static List<SourceRef> readSources(Object raw) {
        List<SourceRef> sources = new List<SourceRef>();
        for (Object item : asList(raw)) {
            Map<String, Object> row = asMap(item);
            SourceRef ref = new SourceRef();
            ref.organization = asString(row.get('organization'));
            ref.title = String.isNotBlank(asString(row.get('document_title')))
                ? asString(row.get('document_title'))
                : asString(row.get('source_name'));
            ref.url = safeUrl(asString(row.get('url')));
            ref.attribution = asString(row.get('attribution_text'));
            ref.trustTier = asString(row.get('trust_tier'));
            String updated = asString(row.get('source_updated_at'));
            if (String.isBlank(updated)) {
                updated = asString(row.get('last_verified_at'));
            }
            ref.updated = String.isNotBlank(updated) && updated.length() >= 10 ? updated.substring(0, 10) : null;
            ref.key = String.isNotBlank(ref.url) ? ref.url : ref.organization + '|' + ref.title;
            if (String.isNotBlank(ref.organization) || String.isNotBlank(ref.url)) {
                sources.add(ref);
            }
        }
        return sources;
    }

    private static List<String> readAliases(Object raw) {
        List<String> aliases = new List<String>();
        Set<String> seen = new Set<String>();
        for (Object item : asList(raw)) {
            String alias = item instanceof Map<String, Object> ? asString(asMap(item).get('alias')) : asString(item);
            if (String.isNotBlank(alias) && !seen.contains(alias.toLowerCase())) {
                seen.add(alias.toLowerCase());
                aliases.add(alias);
            }
        }
        return aliases;
    }

    private static String regionLabel(Map<String, Object> jurisdiction) {
        String country = asString(jurisdiction.get('country'));
        String region = asString(jurisdiction.get('region'));
        if (String.isBlank(country)) {
            return asString(jurisdiction.get('scope')) == 'GLOBAL' ? 'Global' : null;
        }
        return String.isNotBlank(region) && region != country ? country + ' - ' + region : country;
    }

    @TestVisible
    private static String safeUrl(String url) {
        if (String.isBlank(url)) {
            return null;
        }
        String lower = url.trim().toLowerCase();
        return lower.startsWith('https://') || lower.startsWith('http://') ? url.trim() : null;
    }

    private static Boolean isHeadingLine(String line) {
        return line.length() <= 90 && (line.endsWith('?') || !endsWithPunctuation(line));
    }

    private static Boolean endsWithPunctuation(String line) {
        return line.endsWith('.') || line.endsWith('!') || line.endsWith('?') || line.endsWith(':') || line.endsWith(';');
    }

    private static String stripListPrefix(String line) {
        return line.replaceFirst('^[\\-\\*\\u2022\\u2013]\\s*', '').removeEnd(';').trim();
    }

    private static String capitalize(String value) {
        return String.isBlank(value) ? value : value.substring(0, 1).toUpperCase() + value.substring(1);
    }

    private static ContentPart newTextPart(Integer index, String text) {
        ContentPart part = new ContentPart();
        part.key = 'p' + index;
        part.isList = false;
        part.isSubheading = false;
        part.isIntro = false;
        part.text = text;
        part.items = new List<String>();
        return part;
    }

    private static ContentPart newListPart(Integer index) {
        ContentPart part = newTextPart(index, null);
        part.isList = true;
        return part;
    }

    private static void validateSlug(String slug) {
        if (String.isBlank(slug) || !SLUG_PATTERN.matcher(slug).matches()) {
            throw auraError('Please choose a cancer type from the list.');
        }
    }

    private static AuraHandledException auraError(String message) {
        AuraHandledException e = new AuraHandledException(message);
        e.setMessage(message);
        return e;
    }

    private static Map<String, List<String>> buildKeywordMap() {
        Map<String, List<String>> m = new Map<String, List<String>>();
        addKeywords(m, 'symptom sign lump lumps pain ache bleeding discharge swelling bloating feel feeling notice warning dimpling', 'symptoms signs early_detection');
        addKeywords(m, 'treat treated treating treatment therapy therapies cure cured curable manage option options', 'treatment');
        addKeywords(m, 'surgery surgical operation mastectomy lumpectomy removal', 'surgery treatment');
        addKeywords(m, 'chemo chemotherapy', 'chemotherapy treatment');
        addKeywords(m, 'radiation radiotherapy', 'radiation_therapy treatment');
        addKeywords(m, 'immunotherapy immune', 'immunotherapy');
        addKeywords(m, 'targeted antibody antibodies inhibitor', 'targeted_therapy');
        addKeywords(m, 'hormone hormonal endocrine tamoxifen', 'hormone_therapy');
        addKeywords(m, 'transplant stem', 'stem_cell_transplant');
        addKeywords(m, 'drug medicine medication', 'treatment chemotherapy targeted_therapy');
        addKeywords(m, 'screen screening screened mammogram mammography smear colonoscopy', 'screening early_detection');
        addKeywords(m, 'test testing scan biopsy imaging ultrasound mri ct x-ray blood', 'diagnostic_tests diagnosis');
        addKeywords(m, 'diagnose diagnosed diagnosis diagnosing detect detected detection early', 'diagnosis early_detection screening');
        addKeywords(m, 'stage staging spread metastatic metastasis', 'staging');
        addKeywords(m, 'grade grading', 'grading');
        addKeywords(m, 'marker biomarker her2 er pr receptor', 'biomarkers');
        addKeywords(m, 'cause caused causing', 'causes');
        addKeywords(m, 'risk factor age smoking smoke alcohol obesity weight lifestyle', 'risk_factors');
        addKeywords(m, 'gene genetic genetics hereditary inherited inherit family brca brca1 brca2 mutation dna', 'genetics risk_factors causes');
        addKeywords(m, 'prevent prevented prevention preventable avoid reduce lower vaccine hpv', 'prevention');
        addKeywords(m, 'survival survive surviving prognosis outlook expectancy fatal deadly die death', 'prognosis survival');
        addKeywords(m, 'statistic statistics common rate incidence', 'statistics');
        addKeywords(m, 'side effect fatigue nausea hair', 'side_effects');
        addKeywords(m, 'recur recurrence return relapse', 'recurrence follow_up');
        addKeywords(m, 'follow-up followup checkup monitoring', 'follow_up');
        addKeywords(m, 'research trial study studies latest advance', 'research clinical_trials');
        addKeywords(m, 'type subtype kind', 'types_and_subtypes');
        addKeywords(m, 'support supportive living cope coping caregiver carer diet exercise emotional', 'living_with_cancer supportive_care caregiver_information');
        addKeywords(m, 'palliative hospice', 'palliative_care');
        addKeywords(m, 'child children childhood kid', 'childhood_cancer');
        addKeywords(m, 'definition define overview meaning', 'overview');
        return m;
    }

    private static void addKeywords(Map<String, List<String>> m, String tokens, String categories) {
        for (String token : tokens.split(' ')) {
            if (!m.containsKey(token)) {
                m.put(token, new List<String>());
            }
            List<String> existing = m.get(token);
            for (String category : categories.split(' ')) {
                if (!existing.contains(category)) {
                    existing.add(category);
                }
            }
        }
    }

    // Safe JSON accessors -------------------------------------------------------------------------

    private static Map<String, Object> asMap(Object value) {
        return value instanceof Map<String, Object> ? (Map<String, Object>) value : new Map<String, Object>();
    }

    private static List<Object> asList(Object value) {
        return value instanceof List<Object> ? (List<Object>) value : new List<Object>();
    }

    private static String asString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private static Integer asInteger(Object value) {
        if (value instanceof Integer) {
            return (Integer) value;
        }
        if (value instanceof Long) {
            return ((Long) value).intValue();
        }
        if (value instanceof Decimal) {
            return ((Decimal) value).intValue();
        }
        return 0;
    }

    private static List<String> asStringList(Object value) {
        List<String> out = new List<String>();
        for (Object item : asList(value)) {
            if (item != null) {
                out.add(String.valueOf(item));
            }
        }
        return out;
    }

    // ---------------------------------------------------------------------------------------------
    // DTOs returned to Lightning
    // ---------------------------------------------------------------------------------------------

    public class CancerOption implements Comparable {
        @AuraEnabled public String slug;
        @AuraEnabled public String name;
        @AuraEnabled public String site;
        @AuraEnabled public List<String> aliases;
        @AuraEnabled public List<String> categories;
        @AuraEnabled public Integer recordCount;

        public Integer compareTo(Object other) {
            String a = name == null ? '' : name.toLowerCase();
            String b = ((CancerOption) other).name == null ? '' : ((CancerOption) other).name.toLowerCase();
            return a.compareTo(b);
        }
    }

    public class CancerProfile {
        @AuraEnabled public String slug;
        @AuraEnabled public String name;
        @AuraEnabled public String description;
        @AuraEnabled public String site;
        @AuraEnabled public List<String> aliases;
        @AuraEnabled public List<LabelValue> codes;
        @AuraEnabled public List<String> availableCategories;
        @AuraEnabled public List<String> groups;
        @AuraEnabled public String disclaimer;
    }

    public class LabelValue {
        @AuraEnabled public String label;
        @AuraEnabled public String value;

        public LabelValue(String label, String value) {
            this.label = label;
            this.value = value;
        }
    }

    public class Section {
        @AuraEnabled public String category;
        @AuraEnabled public String groupKey;
        @AuraEnabled public String name;
        @AuraEnabled public List<ContentBlock> blocks;
    }

    public class ContentBlock {
        @AuraEnabled public String id;
        @AuraEnabled public String heading;
        @AuraEnabled public String region;
        @AuraEnabled public Boolean isConsensus;
        @AuraEnabled public Boolean truncated;
        @AuraEnabled public List<ContentPart> parts;
        @AuraEnabled public List<SourceRef> sources;
    }

    public class ContentPart {
        @AuraEnabled public String key;
        @AuraEnabled public Boolean isList;
        @AuraEnabled public Boolean isSubheading;
        @AuraEnabled public Boolean isIntro;
        @AuraEnabled public String text;
        @AuraEnabled public List<String> items;
    }

    public class SourceRef {
        @AuraEnabled public String key;
        @AuraEnabled public String organization;
        @AuraEnabled public String title;
        @AuraEnabled public String url;
        @AuraEnabled public String attribution;
        @AuraEnabled public String trustTier;
        @AuraEnabled public String updated;
    }

    public class Evidence {
        @AuraEnabled public String mode;
        @AuraEnabled public List<String> keywords;
        @AuraEnabled public List<String> matchedCategories;
        @AuraEnabled public List<String> matchedGroups;
        @AuraEnabled public List<EvidenceItem> items;
    }

    public class EvidenceItem {
        @AuraEnabled public String key;
        @AuraEnabled public String category;
        @AuraEnabled public String categoryName;
        @AuraEnabled public String groupKey;
        @AuraEnabled public String excerpt;
        @AuraEnabled public String region;
        @AuraEnabled public List<SourceRef> sources;
    }

    private class ScoredItem implements Comparable {
        EvidenceItem item;
        Integer score;

        ScoredItem(EvidenceItem item, Integer score) {
            this.item = item;
            this.score = score;
        }

        public Integer compareTo(Object other) {
            Integer o = ((ScoredItem) other).score;
            return score == o ? 0 : (score > o ? -1 : 1);
        }
    }
}
