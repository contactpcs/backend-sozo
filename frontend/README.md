# Sozo Frontend - Login & Registration Testing

A simple, standalone HTML/CSS/JavaScript frontend to test the Sozo backend login and registration endpoints.

## Features

- **Login**: Test the `/api/v1/users/login` endpoint
- **Registration**: Test the `/api/v1/users/register` endpoint
- **Token Management**: Automatically saves tokens to browser localStorage
- **Real-time Response Display**: Shows API responses in JSON format
- **Responsive Design**: Works on desktop and mobile devices
- **User-friendly UI**: Clean, modern interface with tab-based navigation

## Quick Start

### 1. Make sure your backend is running
```bash
cd backend
python -m uvicorn app.main:app --reload
```

The backend should be running on `http://localhost:8000`.

### 2. Open the frontend
Simply open `index.html` in your web browser:
- Double-click the file, or
- Use Python's built-in server:
  ```bash
  # Navigate to the frontend folder
  cd frontend
  
  # Python 3
  python -m http.server 8080
  
  # Or Python 2
  python -m SimpleHTTPServer 8080
  ```
- Then visit `http://localhost:8080` in your browser

## Test Accounts

Try these test cases:

### Registration
1. Fill in all fields
2. Password must be at least 8 characters
3. Phone number is optional
4. Select a role (Patient, Doctor, Admin)
5. Click "Register"

### Login
1. Use the same email and password you registered with
2. Click "Login"
3. Tokens will be saved to localStorage

## Testing Workflow

1. **Register a new user**
   - Fill in email, name, password, and select a role
   - Click Register
   - Check the Response panel for the created user details

2. **Login with the registered account**
   - Switch to Login tab
   - Enter the same email and password
   - Check the Response panel for the access/refresh tokens

3. **Check localStorage**
   - Open browser DevTools (F12)
   - Go to Application → Storage → Local Storage
   - You'll see `access_token`, `refresh_token`, and `user_email` stored

## Configuration

To change the backend URL, edit `auth.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

## File Structure

```
frontend/
├── index.html          # Main HTML file with form structure
├── styles.css          # Styling and responsive design
├── auth.js             # JavaScript for API calls and form handling
└── README.md           # This file
```

## Keyboard Shortcuts

- **Ctrl + L**: Logout (clears localStorage and switches to login tab)

## Troubleshooting

### CORS Errors
If you get CORS errors, make sure your backend has `http://localhost:8080` in the `cors_origins` list in `config.py`.

### Connection Refused
Make sure your backend is running on `http://localhost:8000`.

### 404 Errors
Check that the endpoint paths match your backend routes:
- Login: `POST /api/v1/users/login`
- Register: `POST /api/v1/users/register`

## Next Steps

After testing, you can:
- Replace with a React/Vue frontend for production
- Add more features like password reset, user profile
- Integrate with your backend authentication flow
- Add protected routes that require JWT tokens

## Browser Support

Works on all modern browsers:
- Chrome/Edge 60+
- Firefox 55+
- Safari 12+
