/**
 * @description Unit tests for CancerInfoController and CancerInfoApiClient.
 *              All callouts are served by an in-memory HttpCalloutMock - no real network traffic.
 */
@IsTest
private class CancerInfoControllerTest {
    private static final String PREFIX = 'callout:CancerInfo_API';

    // ---------------------------------------------------------------------------------------------
    // Mock
    // ---------------------------------------------------------------------------------------------

    /** Routes requests by path (query string ignored). Unknown paths return 404. */
    private class RouterMock implements HttpCalloutMock {
        private final Map<String, HttpResponse> routes = new Map<String, HttpResponse>();
        public final List<String> endpoints = new List<String>();
        public Boolean failTransport = false;

        public RouterMock route(String path, Integer status, String body) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(status);
            res.setHeader('Content-Type', 'application/json');
            res.setBody(body);
            routes.put(path, res);
            return this;
        }

        public RouterMock route(String path, Object payload) {
            return route(path, 200, JSON.serialize(payload));
        }

        public HttpResponse respond(HttpRequest req) {
            endpoints.add(req.getEndpoint());
            Assert.areEqual('GET', req.getMethod(), 'Only GET requests are expected');
            if (failTransport) {
                throw new CalloutException('Read timed out');
            }
            String path = req.getEndpoint().removeStart(PREFIX).substringBefore('?');
            if (routes.containsKey(path)) {
                return routes.get(path);
            }
            HttpResponse notFound = new HttpResponse();
            notFound.setStatusCode(404);
            notFound.setBody('{"error":{"code":"NOT_FOUND"}}');
            return notFound;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Fixtures (shapes copied from live https://cancerinfo-api.onrender.com responses)
    // ---------------------------------------------------------------------------------------------

    private static Map<String, Object> envelope(Object data) {
        return new Map<String, Object>{
            'data' => data,
            'meta' => new Map<String, Object>{ 'api_version' => 'v1', 'disclaimer' => 'Informational only.' }
        };
    }

    private static Map<String, Object> source(String org, String url) {
        return new Map<String, Object>{
            'organization' => org,
            'source_name' => org + ' database',
            'document_title' => org + ' page',
            'url' => url,
            'attribution_text' => 'Adapted from ' + org + '.',
            'trust_tier' => 'Tier 1 - Primary Authoritative',
            'source_updated_at' => '2026-09-12T06:23:36.495689Z'
        };
    }

    private static Map<String, Object> record(String id, String content, String country, List<Object> sources) {
        return new Map<String, Object>{
            'id' => id,
            'content' => content,
            'jurisdiction' => new Map<String, Object>{ 'scope' => 'COUNTRY', 'country' => country, 'region' => null },
            'sources' => sources
        };
    }

    private static Map<String, Object> category(String key, String name, List<Object> records) {
        return envelope(
            new Map<String, Object>{
                'category' => key,
                'category_name' => name,
                'consensus_summary' => null,
                'items' => null,
                'records' => records
            }
        );
    }

    private static final String BREAST_SYMPTOMS =
        'Symptoms of breast cancer include a new lump or thickening in the breast or underarm, changes in the size ' +
        'or shape of the breast, dimpling or puckering of the breast skin, an inverted nipple, and nipple discharge ' +
        'other than breast milk (including blood).';

    private static final String BREAST_TREATMENT =
        'Treatment for breast cancer depends on the subtype, stage, biomarker status (ER, PR, HER2), and general health. ' +
        'Modalities include surgery (lumpectomy or mastectomy), radiation therapy, systemic chemotherapy, targeted ' +
        'therapy (e.g., anti-HER2 monoclonal antibodies), and hormone (endocrine) therapy for hormone-receptor-positive tumors.';

    private static final String OVARIAN_CAUSES =
        'Main causes of ovarian cancer\n' +
        'The risk of developing ovarian cancer increases with age.\n' +
        'You may have a higher chance of getting ovarian cancer if you:\n' +
        'inherited a faulty gene, such as the BRCA genes\n' +
        'had breast cancer or bowel cancer\n' +
        'have endometriosis or diabetes\n' +
        'It is still possible to get ovarian cancer even if you have none of these.';

    private static RouterMock breastMock() {
        RouterMock mock = new RouterMock();
        mock.route(
            '/v1/cancers',
            envelope(
                new List<Object>{
                    new Map<String, Object>{
                        'slug' => 'ovarian-cancer',
                        'canonical_name' => 'Ovarian cancer',
                        'anatomical_site' => null,
                        'aliases' => new List<Object>{ 'ovary cancer' }
                    },
                    new Map<String, Object>{
                        'slug' => 'breast-cancer',
                        'canonical_name' => 'Breast Cancer',
                        'anatomical_site' => 'Breast',
                        'aliases' => new List<Object>{ 'Mammary Carcinoma', 'Breast Carcinoma' }
                    },
                    new Map<String, Object>{ 'slug' => 'BAD SLUG!', 'canonical_name' => 'Ignored' }
                }
            )
        );
        mock.route(
            '/v1/coverage',
            envelope(
                new Map<String, Object>{
                    'cancers' => new List<Object>{
                        new Map<String, Object>{
                            'slug' => 'breast-cancer',
                            'total_records' => 4,
                            'categories_covered' => new List<Object>{ 'overview', 'screening', 'symptoms', 'treatment' }
                        }
                    }
                }
            )
        );
        mock.route(
            '/v1/cancers/breast-cancer',
            envelope(
                new Map<String, Object>{
                    'slug' => 'breast-cancer',
                    'canonical_name' => 'Breast Cancer',
                    'description' => 'Cancer that forms in the cells of the breasts.',
                    'anatomical_site' => 'Breast',
                    'aliases' => new List<Object>{
                        new Map<String, Object>{ 'alias' => 'Breast Carcinoma' },
                        new Map<String, Object>{ 'alias' => 'breast carcinoma' },
                        new Map<String, Object>{ 'alias' => 'Mammary Carcinoma' }
                    },
                    'taxonomy_codes' => new Map<String, Object>{ 'MeSH' => 'D001943', 'ICD-O-3' => 'C50', 'Empty' => '' },
                    'available_categories' => new List<Object>{ 'overview', 'screening', 'symptoms', 'treatment' }
                }
            )
        );
        mock.route(
            '/v1/cancers/breast-cancer/symptoms',
            category(
                'symptoms',
                'Symptoms',
                new List<Object>{
                    record('s1', BREAST_SYMPTOMS, 'US', new List<Object>{ source('National Cancer Institute', 'https://www.cancer.gov/types/breast/symptoms') }),
                    record('s2', BREAST_SYMPTOMS, 'US', new List<Object>()) // duplicate content is dropped
                }
            )
        );
        mock.route(
            '/v1/cancers/breast-cancer/treatment',
            category(
                'treatment',
                'Treatment',
                new List<Object>{
                    record('t1', BREAST_TREATMENT, 'US', new List<Object>{ source('National Cancer Institute', 'javascript:alert(1)') })
                }
            )
        );
        mock.route(
            '/v1/search',
            envelope(
                new Map<String, Object>{
                    'query' => 'lump',
                    'results' => new List<Object>{
                        new Map<String, Object>{
                            'match_type' => 'content_record',
                            'cancer' => new Map<String, Object>{ 'slug' => 'ovarian-cancer' },
                            'category' => 'symptoms',
                            'record' => record('o1', 'A lump in the tummy.', 'GB', new List<Object>())
                        },
                        new Map<String, Object>{
                            'match_type' => 'cancer',
                            'cancer' => new Map<String, Object>{ 'slug' => 'breast-cancer' },
                            'category' => null,
                            'record' => null
                        },
                        new Map<String, Object>{
                            'match_type' => 'content_record',
                            'cancer' => new Map<String, Object>{ 'slug' => 'breast-cancer' },
                            'category' => 'treatment',
                            'record' => record('t1', BREAST_TREATMENT, 'US', new List<Object>())
                        }
                    }
                }
            )
        );
        return mock;
    }

    // ---------------------------------------------------------------------------------------------
    // getCancers
    // ---------------------------------------------------------------------------------------------

    @IsTest
    static void getCancersReturnsSortedOptionsWithCoverage() {
        RouterMock mock = breastMock();
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        List<CancerInfoController.CancerOption> options = CancerInfoController.getCancers();
        Test.stopTest();

        Assert.areEqual(2, options.size(), 'Invalid slugs must be skipped');
        Assert.areEqual('Breast Cancer', options[0].name, 'Options must be sorted by name');
        Assert.areEqual(4, options[0].recordCount, 'Coverage record count expected');
        Assert.areEqual(4, options[0].categories.size(), 'Coverage categories expected');
        Assert.areEqual(2, options[0].aliases.size());
        Assert.areEqual(0, options[1].recordCount, 'Cancers without coverage default to 0');
        Assert.isTrue(mock.endpoints[0].startsWith(PREFIX + '/v1/cancers?'), 'Must call through the Named Credential');
    }

    @IsTest
    static void getCancersStillWorksWhenCoverageFails() {
        RouterMock mock = breastMock();
        mock.route('/v1/coverage', 503, 'Service Unavailable');
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        List<CancerInfoController.CancerOption> options = CancerInfoController.getCancers();
        Test.stopTest();

        Assert.areEqual(2, options.size());
        Assert.areEqual(0, options[0].recordCount);
    }

    @IsTest
    static void getCancersSurfacesServerErrors() {
        RouterMock mock = new RouterMock().route('/v1/cancers', 500, '{}');
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        try {
            CancerInfoController.getCancers();
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('HTTP 500'), e.getMessage());
        }
        Test.stopTest();
    }

    @IsTest
    static void transportFailureGivesFriendlyMessage() {
        RouterMock mock = breastMock();
        mock.failTransport = true;
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        try {
            CancerInfoController.getCancers();
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('waking up'), e.getMessage());
        }
        Test.stopTest();
    }

    @IsTest
    static void unreadableBodyGivesFriendlyMessage() {
        RouterMock mock = new RouterMock().route('/v1/cancers', 200, '<html>not json</html>');
        mock.route('/v1/cancers/breast-cancer', 200, '[1,2,3]');
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        try {
            CancerInfoController.getCancers();
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('could not be read'), e.getMessage());
        }
        try {
            CancerInfoController.getCancerProfile('breast-cancer');
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('could not be read'), e.getMessage());
        }
        Test.stopTest();
    }

    // ---------------------------------------------------------------------------------------------
    // getCancerProfile
    // ---------------------------------------------------------------------------------------------

    @IsTest
    static void getCancerProfileMapsHeaderAndGroups() {
        Test.setMock(HttpCalloutMock.class, breastMock());

        Test.startTest();
        CancerInfoController.CancerProfile profile = CancerInfoController.getCancerProfile('breast-cancer');
        Test.stopTest();

        Assert.areEqual('Breast Cancer', profile.name);
        Assert.areEqual('Breast', profile.site);
        Assert.areEqual(2, profile.aliases.size(), 'Aliases are de-duplicated case-insensitively');
        Assert.areEqual(2, profile.codes.size(), 'Blank taxonomy codes are dropped');
        Assert.areEqual('ICD-O-3', profile.codes[0].label, 'Codes are sorted');
        Assert.areEqual('Informational only.', profile.disclaimer);
        Assert.areEqual(
            new List<String>{ 'overview', 'treatment', 'symptoms', 'diagnosis' },
            profile.groups,
            'Only groups with data, in display order'
        );
    }

    @IsTest
    static void getCancerProfileRejectsInvalidSlug() {
        Test.setMock(HttpCalloutMock.class, breastMock());
        for (String bad : new List<String>{ null, '', '../admin', 'Breast Cancer', 'x?y=1' }) {
            try {
                CancerInfoController.getCancerProfile(bad);
                Assert.fail('Expected rejection for ' + bad);
            } catch (AuraHandledException e) {
                Assert.isTrue(e.getMessage().contains('choose a cancer'), e.getMessage());
            }
        }
    }

    @IsTest
    static void getCancerProfileNotFound() {
        Test.setMock(HttpCalloutMock.class, new RouterMock());
        try {
            CancerInfoController.getCancerProfile('unknown-cancer');
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('No information'), e.getMessage());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // getSectionGroup
    // ---------------------------------------------------------------------------------------------

    @IsTest
    static void getSectionGroupParsesInlineListsIntoBullets() {
        Test.setMock(HttpCalloutMock.class, breastMock());
        List<String> available = new List<String>{ 'overview', 'screening', 'symptoms', 'treatment' };

        Test.startTest();
        List<CancerInfoController.Section> symptoms = CancerInfoController.getSectionGroup('breast-cancer', 'symptoms', available);
        List<CancerInfoController.Section> treatment = CancerInfoController.getSectionGroup('breast-cancer', 'treatment', available);
        Test.stopTest();

        Assert.areEqual(1, symptoms.size());
        Assert.areEqual('symptoms', symptoms[0].groupKey);
        Assert.areEqual(1, symptoms[0].blocks.size(), 'Duplicate records are removed');
        CancerInfoController.ContentBlock block = symptoms[0].blocks[0];
        Assert.areEqual('US', block.region);
        Assert.areEqual('https://www.cancer.gov/types/breast/symptoms', block.sources[0].url);
        Assert.areEqual('2026-09-12', block.sources[0].updated);
        CancerInfoController.ContentPart listPart = block.parts[block.parts.size() - 1];
        Assert.isTrue(listPart.isList);
        Assert.areEqual(5, listPart.items.size(), String.valueOf(listPart.items));
        Assert.areEqual('A new lump or thickening in the breast or underarm', listPart.items[0]);
        Assert.areEqual('Nipple discharge other than breast milk (including blood)', listPart.items[4]);

        CancerInfoController.ContentBlock tBlock = treatment[0].blocks[0];
        Assert.isNull(tBlock.sources[0].url, 'Non-http URLs must be discarded');
        Assert.areEqual(3, tBlock.parts.size(), 'Lead sentence, intro and bullet list');
        Assert.isFalse(tBlock.parts[0].isList);
        Assert.isTrue(tBlock.parts[1].isIntro);
        Assert.areEqual(5, tBlock.parts[2].items.size(), String.valueOf(tBlock.parts[2].items));
        Assert.areEqual('Targeted therapy (e.g., anti-HER2 monoclonal antibodies)', tBlock.parts[2].items[3]);
    }

    @IsTest
    static void getSectionGroupParsesMultiLineContent() {
        RouterMock mock = new RouterMock();
        Map<String, Object> payload = category(
            'causes',
            null,
            new List<Object>{ record('c1', OVARIAN_CAUSES, 'GB', new List<Object>{ source('National Health Service', 'https://www.nhs.uk/x') }) }
        );
        ((Map<String, Object>) payload.get('data')).put('consensus_summary', 'Age and inherited genes raise risk.');
        mock.route('/v1/cancers/ovarian-cancer/causes', payload);
        Test.setMock(HttpCalloutMock.class, mock);

        Test.startTest();
        List<CancerInfoController.Section> sections = CancerInfoController.getSectionGroup(
            'ovarian-cancer',
            'causes',
            new List<String>{ 'causes' }
        );
        Test.stopTest();

        Assert.areEqual(1, sections.size());
        Assert.areEqual('Causes', sections[0].name, 'Falls back to a label built from the category key');
        Assert.areEqual(2, sections[0].blocks.size(), 'Consensus summary plus the record');
        Assert.isTrue(sections[0].blocks[0].isConsensus);

        CancerInfoController.ContentBlock block = sections[0].blocks[1];
        Assert.areEqual('Main causes of ovarian cancer', block.heading);
        Assert.areEqual(4, block.parts.size(), String.valueOf(block.parts));
        Assert.isTrue(block.parts[1].text.endsWith(':'));
        Assert.isTrue(block.parts[2].isList);
        Assert.areEqual(3, block.parts[2].items.size());
        Assert.areEqual('Inherited a faulty gene, such as the BRCA genes', block.parts[2].items[0]);
        Assert.isFalse(block.parts[3].isList, 'Trailing sentence stays a paragraph');
    }

    @IsTest
    static void getSectionGroupSkipsMissingCategories() {
        Test.setMock(HttpCalloutMock.class, breastMock());

        Test.startTest();
        // 'overview' is available but has no route -> 404 -> skipped; 'types_and_subtypes' is unavailable -> no callout.
        List<CancerInfoController.Section> sections = CancerInfoController.getSectionGroup(
            'breast-cancer',
            'overview',
            new List<String>{ 'overview' }
        );
        List<CancerInfoController.Section> none = CancerInfoController.getSectionGroup('breast-cancer', 'research', null);
        Test.stopTest();

        Assert.isTrue(sections.isEmpty(), 'Empty groups return no sections so no card renders');
        Assert.isTrue(none.isEmpty());
    }

    @IsTest
    static void getSectionGroupThrowsWhenEveryCategoryFails() {
        RouterMock mock = new RouterMock().route('/v1/cancers/breast-cancer/symptoms', 502, 'Bad gateway');
        Test.setMock(HttpCalloutMock.class, mock);
        try {
            CancerInfoController.getSectionGroup('breast-cancer', 'symptoms', new List<String>{ 'symptoms' });
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('HTTP 502'), e.getMessage());
        }
    }

    @IsTest
    static void getSectionGroupRejectsUnknownGroup() {
        try {
            CancerInfoController.getSectionGroup('breast-cancer', 'billing', new List<String>());
            Assert.fail('Expected an AuraHandledException');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('Unknown section'), e.getMessage());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // findEvidence
    // ---------------------------------------------------------------------------------------------

    @IsTest
    static void findEvidenceRanksPassagesForAQuestion() {
        RouterMock mock = breastMock();
        Test.setMock(HttpCalloutMock.class, mock);
        List<String> available = new List<String>{ 'overview', 'screening', 'symptoms', 'treatment' };

        Test.startTest();
        CancerInfoController.Evidence result = CancerInfoController.findEvidence(
            'breast-cancer',
            'Is a lump in the breast always a symptom of breast cancer?',
            'question',
            available
        );
        Test.stopTest();

        Assert.areEqual('question', result.mode);
        Assert.areEqual(new List<String>{ 'lump', 'symptom' }, result.keywords, 'Stopwords and cancer name removed');
        Assert.isTrue(result.matchedCategories.contains('symptoms'));
        Assert.isFalse(result.matchedCategories.contains('signs'), 'Only categories the cancer has');
        Assert.areEqual(new List<String>{ 'symptoms' }, result.matchedGroups, 'early_detection is not available for this cancer');
        Assert.areEqual(2, result.items.size(), 'Duplicate passages (same text, different id) are collapsed');
        Assert.isFalse(result.items.isEmpty());
        Assert.areEqual('symptoms', result.items[0].category, 'Best keyword match ranks first');
        Assert.isTrue(result.items[0].excerpt.toLowerCase().contains('lump'));
        for (CancerInfoController.EvidenceItem item : result.items) {
            Assert.areNotEqual('o1', item.key, 'Search hits for other cancers are filtered out');
        }
        Boolean searchedWithCancerName = false;
        for (String endpoint : mock.endpoints) {
            if (endpoint.contains('/v1/search') && endpoint.contains('breast')) {
                searchedWithCancerName = true;
            }
        }
        Assert.isTrue(searchedWithCancerName, 'Search is biased toward the selected cancer');
    }

    @IsTest
    static void findEvidenceForAClaimUsesSearchHits() {
        Test.setMock(HttpCalloutMock.class, breastMock());

        Test.startTest();
        CancerInfoController.Evidence result = CancerInfoController.findEvidence(
            'breast-cancer',
            'Mastectomy is the only treatment for breast cancer',
            'CLAIM',
            new List<String>{ 'treatment' }
        );
        Test.stopTest();

        Assert.areEqual('claim', result.mode);
        Assert.areEqual(1, result.items.size(), 'Same record from category and search is de-duplicated');
        Assert.areEqual('Treatment', result.items[0].categoryName);
        Assert.areEqual('treatment', result.items[0].groupKey);
    }

    @IsTest
    static void findEvidenceWithOnlyStopwordsMakesNoCallouts() {
        RouterMock mock = breastMock();
        Test.setMock(HttpCalloutMock.class, mock);

        CancerInfoController.Evidence result = CancerInfoController.findEvidence(
            'breast-cancer',
            'Is it true?',
            'claim',
            null
        );

        Assert.isTrue(result.keywords.isEmpty());
        Assert.isTrue(result.items.isEmpty());
        Assert.isTrue(mock.endpoints.isEmpty(), 'No callouts without keywords');
    }

    @IsTest
    static void findEvidenceSurvivesSearchFailure() {
        RouterMock mock = breastMock();
        mock.route('/v1/search', 500, '{}');
        Test.setMock(HttpCalloutMock.class, mock);

        CancerInfoController.Evidence result = CancerInfoController.findEvidence(
            'breast-cancer',
            'new lump',
            'question',
            new List<String>{ 'symptoms', 'screening' }
        );

        Assert.areEqual(1, result.items.size(), 'Category passages are still returned');
    }

    @IsTest
    static void findEvidenceValidatesInput() {
        String tooLong = 'a'.repeat(CancerInfoController.MAX_INPUT_LENGTH + 1);
        for (String text : new List<String>{ null, '   ', tooLong }) {
            try {
                CancerInfoController.findEvidence('breast-cancer', text, 'question', null);
                Assert.fail('Expected rejection');
            } catch (AuraHandledException e) {
                Assert.isTrue(e.getMessage().startsWith('Please'), e.getMessage());
            }
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Helper units
    // ---------------------------------------------------------------------------------------------

    @IsTest
    static void helpersBehave() {
        Assert.areEqual('', CancerInfoApiClient.buildQuery(null));
        Assert.areEqual('', CancerInfoApiClient.buildQuery(new Map<String, String>{ 'q' => ' ' }));
        Assert.areEqual(
            '?limit=10&q=lump+%26+pain',
            CancerInfoApiClient.buildQuery(new Map<String, String>{ 'q' => 'lump & pain', 'limit' => '10' })
        );

        Assert.areEqual('Types & Subtypes', CancerInfoController.categoryLabel('types_and_subtypes'));
        Assert.areEqual('General', CancerInfoController.categoryLabel(null));
        Assert.areEqual('living', CancerInfoController.groupOf('side_effects'));
        Assert.areEqual('overview', CancerInfoController.groupOf('unknown_category'));

        Assert.isNull(CancerInfoController.safeUrl('javascript:alert(1)'));
        Assert.isNull(CancerInfoController.safeUrl(null));
        Assert.areEqual('https://a.org', CancerInfoController.safeUrl(' https://a.org '));

        Assert.areEqual(
            new List<String>{ 'Surgery (a, b)', 'radiation', 'chemo' },
            new List<String>{
                CancerInfoController.splitTopLevel('Surgery (a, b), radiation and chemo')[0],
                CancerInfoController.splitTopLevel('Surgery (a, b), radiation and chemo')[1],
                CancerInfoController.splitTopLevel('Surgery (a, b), radiation and chemo')[2]
            }
        );

        Assert.areEqual(new List<String>{ 'genetics', 'risk_factors', 'causes' }, CancerInfoController.matchCategories(new List<String>{ 'brca' }));
        Assert.isTrue(CancerInfoController.matchCategories(new List<String>{ 'scans' }).contains('diagnostic_tests'), 'Plural fallback');
        Assert.isTrue(CancerInfoController.matchCategories(new List<String>{ 'xyz' }).isEmpty());
    }

    @IsTest
    static void longContentIsTruncated() {
        String sentence = 'Screening tests look for cancer before symptoms appear. ';
        String longText = sentence.repeat(80);
        CancerInfoController.ContentBlock block = CancerInfoController.buildBlock(null, longText, 'US', new List<CancerInfoController.SourceRef>());

        Assert.isTrue(block.truncated);
        Assert.isNotNull(block.id);
        Integer total = 0;
        for (CancerInfoController.ContentPart part : block.parts) {
            total += part.text == null ? 0 : part.text.length();
        }
        Assert.isTrue(total <= CancerInfoController.MAX_CONTENT_LENGTH, 'Content capped at MAX_CONTENT_LENGTH');

        String excerpt = CancerInfoController.bestExcerpt(longText, new List<String>{ 'nothing-matches' });
        Assert.isTrue(excerpt.endsWith('...'));
        Assert.isTrue(excerpt.length() <= 420);
    }

    @IsTest
    static void sentenceStyleListsStayTogether() {
        List<CancerInfoController.ContentPart> parts = CancerInfoController.parseLines(
            new List<String>{
                'Treatment of dysgerminoma may include:',
                'Surgery to remove the ovary, followed by chemotherapy.',
                'A clinical trial of a new treatment.',
                'Use the clinical trial search to find trials that are accepting patients. ' + 'x'.repeat(220)
            }
        );
        Assert.areEqual(3, parts.size(), String.valueOf(parts));
        Assert.isTrue(parts[1].isList);
        Assert.areEqual(2, parts[1].items.size(), 'Period-terminated items after a colon continue the list');
        Assert.isFalse(parts[2].isList, 'A long paragraph ends the list');
    }

    @IsTest
    static void loneShortLineBecomesSubheading() {
        List<CancerInfoController.ContentPart> parts = CancerInfoController.parseLines(
            new List<String>{ 'Referral to a specialist', 'The GP may refer you for more tests.' }
        );
        Assert.areEqual(2, parts.size());
        Assert.isTrue(parts[0].isSubheading);
        Assert.isFalse(parts[0].isList);
    }
}
