import json
import requests
from app.auth.jwt import create_access_token

# generate token for a test user
token = create_access_token(subject="diag-user", user_id=1, role="admin")
print('Generated token (truncated):', token[:64] + '...')
headers = {"Authorization": f"Bearer {token}"}
url = "http://127.0.0.1:8000/api/metrics/resources/13"
try:
    r = requests.get(url, headers=headers, timeout=15)
    print('Status:', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
except Exception as e:
    print('Request failed:', e)
