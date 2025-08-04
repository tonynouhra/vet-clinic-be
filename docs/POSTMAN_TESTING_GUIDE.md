# Postman Testing Guide for Vet Clinic Backend

This guide shows you how to test the API authentication with Postman using the development endpoints.

## Quick Start

### 1. Get Available Test Users
**GET** `http://localhost:8000/api/v1/auth/dev-users`

This returns a list of test users you can use:
- `admin@vetclinic.com` - Admin with full access
- `vet@vetclinic.com` - Veterinarian 
- `receptionist@vetclinic.com` - Receptionist
- `owner@example.com` - Pet owner

### 2. Login and Get Token
**POST** `http://localhost:8000/api/v1/auth/dev-login`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "email": "admin@vetclinic.com",
  "password": "dev-password"
}
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "user_admin",
    "email": "admin@vetclinic.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin"
  },
  "message": "Development token generated successfully. Use this token in Authorization header: Bearer <token>"
}
```

### 3. Test Token Authentication
**GET** `http://localhost:8000/api/v1/auth/test-token`

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response:**
```json
{
  "message": "Token authentication successful!",
  "user": {
    "user_id": "user_admin",
    "email": "admin@vetclinic.com",
    "role": "admin",
    "exp": 1234567890
  },
  "instructions": [
    "Your token is working correctly",
    "You can now use this token to access protected endpoints",
    "Add 'Authorization: Bearer <your-token>' to all API requests"
  ]
}
```

## Using Tokens in Postman

### Method 1: Manual Header
Add to every request:
```
Authorization: Bearer <your-token-here>
```

### Method 2: Postman Collection Variables
1. Create a collection variable called `auth_token`
2. After login, copy the token value
3. Set the collection variable to the token
4. Use `{{auth_token}}` in Authorization headers

### Method 3: Postman Pre-request Script
Add this to your collection's pre-request script:
```javascript
// Auto-login if no token exists
if (!pm.collectionVariables.get("auth_token")) {
    pm.sendRequest({
        url: 'http://localhost:8000/api/v1/auth/dev-login',
        method: 'POST',
        header: {
            'Content-Type': 'application/json'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify({
                "email": "admin@vetclinic.com",
                "password": "dev-password"
            })
        }
    }, function (err, response) {
        if (!err && response.code === 200) {
            const token = response.json().token;
            pm.collectionVariables.set("auth_token", token);
        }
    });
}
```

## Test Different User Roles

### Admin User
```json
{
  "email": "admin@vetclinic.com",
  "password": "dev-password"
}
```

### Veterinarian
```json
{
  "email": "vet@vetclinic.com", 
  "password": "dev-password"
}
```

### Receptionist
```json
{
  "email": "receptionist@vetclinic.com",
  "password": "dev-password"
}
```

### Pet Owner
```json
{
  "email": "owner@example.com",
  "password": "dev-password"
}
```

## Token Details

- **Expiration**: 24 hours
- **Algorithm**: HS256
- **Contains**: user_id, email, role, expiration time
- **Usage**: Add to Authorization header as `Bearer <token>`

## Troubleshooting

### "Token has expired"
- Get a new token using `/auth/dev-login`
- Tokens last 24 hours

### "Invalid token"
- Check that you're using `Bearer ` prefix
- Ensure token is copied completely
- Verify you're using the development endpoints

### "Endpoint not available in production"
- These endpoints only work when `ENVIRONMENT=development`
- Check your `.env` file

## Next Steps

Once you've tested the authentication:
1. Use the token to test other protected endpoints
2. Test different user roles and permissions
3. Verify role-based access control is working
4. Test token expiration handling

## Important Notes

⚠️ **Development Only**: These endpoints are disabled in production
⚠️ **Mock Data**: Users are mocked for testing, not real Clerk users yet
⚠️ **Security**: Don't use these patterns in production code