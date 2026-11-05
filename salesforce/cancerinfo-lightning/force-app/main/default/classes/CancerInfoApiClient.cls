/**
 * @description Thin, read-only HTTP client for the public CancerInfo API
 *              (https://cancerinfo-api.onrender.com). Every request goes through the
 *              CancerInfo_API Named Credential, so the endpoint is never hard-coded and
 *              no Remote Site Setting is needed.
 */
public with sharing class CancerInfoApiClient {
    /** Named Credential merge prefix (see namedCredentials/CancerInfo_API). */
    public static final String NAMED_CREDENTIAL = 'callout:CancerInfo_API';

    /**
     * The API is hosted on a free tier that sleeps when idle; the first request can take
     * up to a minute. Apex allows 120 s per request and 120 s cumulative per transaction.
     */
    @TestVisible
    private static final Integer TIMEOUT_MS = 60000;

    /** Raised for any transport, HTTP or parsing failure, with a user-safe message. */
    public class CancerInfoApiException extends Exception {
        public Integer statusCode;
    }

    /**
     * @description Performs a GET request and returns the parsed top-level JSON object.
     * @param path  API path beginning with '/', for example '/v1/cancers'.
     * @param query Optional query parameters; blank values are skipped. Values are URL-encoded.
     * @return Parsed JSON object (the API always wraps results in {"data": ..., "meta": ...}).
     */
    public static Map<String, Object> get(String path, Map<String, String> query) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + path + buildQuery(query));
        req.setMethod('GET');
        req.setHeader('Accept', 'application/json');
        req.setTimeout(TIMEOUT_MS);

        HttpResponse res;
        try {
            res = new Http().send(req);
        } catch (System.CalloutException e) {
            throw newException(
                'The CancerInfo API did not respond in time. It may be waking up - please try again in a moment.',
                0
            );
        }

        Integer code = res.getStatusCode();
        if (code == 404) {
            throw newException('No information was found for this request.', code);
        }
        if (code < 200 || code >= 300) {
            throw newException('The CancerInfo API returned an error (HTTP ' + code + '). Please try again later.', code);
        }

        Object parsed;
        try {
            parsed = JSON.deserializeUntyped(res.getBody());
        } catch (JSONException e) {
            throw newException('The CancerInfo API returned a response that could not be read.', code);
        }
        if (!(parsed instanceof Map<String, Object>)) {
            throw newException('The CancerInfo API returned a response that could not be read.', code);
        }
        return (Map<String, Object>) parsed;
    }

    /**
     * @description Builds a deterministic, URL-encoded query string.
     */
    @TestVisible
    private static String buildQuery(Map<String, String> query) {
        if (query == null || query.isEmpty()) {
            return '';
        }
        List<String> keys = new List<String>(query.keySet());
        keys.sort();
        List<String> parts = new List<String>();
        for (String key : keys) {
            String value = query.get(key);
            if (String.isBlank(value)) {
                continue;
            }
            parts.add(EncodingUtil.urlEncode(key, 'UTF-8') + '=' + EncodingUtil.urlEncode(value, 'UTF-8'));
        }
        return parts.isEmpty() ? '' : '?' + String.join(parts, '&');
    }

    private static CancerInfoApiException newException(String message, Integer statusCode) {
        CancerInfoApiException ex = new CancerInfoApiException(message);
        ex.statusCode = statusCode;
        return ex;
    }
}
