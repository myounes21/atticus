#!/bin/bash
export $(grep -v '^#' .env | xargs)
TOKEN=$(curl -s -X POST 'http://localhost:8000/auth/login' -d '{"email":"demo.lawyer@atticus.local","password":"DemoPass!123"}' -H 'Content-Type: application/json' | jq -r .access_token)
CASE_ID=$(curl -s -X GET "http://localhost:8000/cases" -H "Authorization: Bearer $TOKEN" | jq -r '.cases[0].case_id')

echo "Running Cache Miss Query..."
QUERY="What is the exact sum mentioned in the final judgement? $(date +%s)"
time curl -s -o /dev/null -w "%{time_total}\n" -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CASE_ID\",\"query\":\"$QUERY\",\"stream\":false}"

echo "Running Cache Hit Query (same query)..."
time curl -s -o /dev/null -w "%{time_total}\n" -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CASE_ID\",\"query\":\"$QUERY\",\"stream\":false}"
