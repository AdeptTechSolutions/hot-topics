import requests

url = "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live"
payload = '[{"keyword":"seo", "location_code":2840, "language_code":"en", "depth":3, "include_seed_keyword":false, "include_serp_info":false, "ignore_synonyms":false, "include_clickstream_data":false, "replace_with_core_keyword":false, "limit":100}]'
headers = {
    "Authorization": "Basic bXVoYW1tYWQudW1lckBhZGVwdC10ZWNoc29sdXRpb25zLmNvbTo1NDgxOTdiMDAwNmZjMzk1",
    "Content-Type": "application/json",
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
