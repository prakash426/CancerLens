curl -X POST "https://api.meta.ai/v1/responses" \
 -H "Authorization: Bearer $META_API_KEY" \
 -H "Content-Type: application/json" \
 -d '{
"model": "muse-spark-1.3",
"input": "What is the capital of France?"
}'
