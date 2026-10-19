# Google sign-in setup

## Google Cloud setup

1. Open the Google Cloud Console and select or create the project for BobTronics.
2. Configure the OAuth consent screen with the app name and support email.
3. Create an OAuth client ID with application type **Web application**.
4. Add the frontend's local and deployed origins under **Authorized JavaScript origins** (for example, `http://localhost:5173`).
5. Copy the client ID. The backend ID-token flow does not need a client secret.

## Backend setup

1. Put the client ID in your local `.env` file:

   ```env
   GOOGLE_OAUTH_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
   ```

2. Set the same `GOOGLE_OAUTH_CLIENT_ID` environment variable in the deployed backend.
3. Install backend dependencies and apply the database migration:

   ```powershell
   pip install -r requirements.txt
   python manage.py migrate
   ```

## Frontend request

Use Google Identity Services to get the user's ID token, then send it to `POST /api/v1/auth/google/`:

```json
{
  "credential": "google-id-token"
}
```

On success, the API returns the BobTronics user profile and JWT access/refresh tokens. The backend verifies the token's signature, issuer, expiry, and audience against `GOOGLE_OAUTH_CLIENT_ID`. It uses Google's stable account ID to link future sign-ins. New or linked accounts must use a verified Gmail or Google Workspace address; an existing account with another email type must first use the regular email/password login.
