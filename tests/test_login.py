import requests

# Test login endpoint with the correct password
url = 'http://localhost:8001/auth/token'
data = {
    'username': 'denzylibe6',
    'password': 'qwerty23'
}

try:
    response = requests.post(url, data=data)
    print(f'Status Code: {response.status_code}')
    if response.status_code == 200:
        print('Login successful!')
        result = response.json()
        print(f'Access Token: {result["access_token"][:50]}...')
        print(f'Token Type: {result["token_type"]}')
    else:
        print(f'Login failed: {response.text}')
except Exception as e:
    print(f'Request failed: {e}')
