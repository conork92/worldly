# Authentication Setup Guide

This app now uses API key authentication to protect write operations (POST, PATCH, DELETE).

## Setup Steps

### 1. Add API Key to Environment Variables

Add your API key to the `.env` file in the `app/` directory:

```bash
API_KEY=your-secret-api-key-here
```

**Important:** Choose a strong, random API key. You can generate one using:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Restart the Server

After adding the API key, restart your FastAPI server:
```bash
cd app
make start
```

### 3. First-Time Frontend Setup

When you first visit any page that needs to write data (books, quotes, or albums pages), you'll be prompted to enter your API key. This key will be stored in your browser's localStorage and used for all subsequent requests.

**Note:** The API key is stored locally in your browser - it's not sent to any third party, only to your own API server.

## Protected Endpoints

The following endpoints now require authentication:

- `POST /api/quotes` - Create a new quote
- `PATCH /api/books/{book_id}` - Update a book's country
- `PATCH /api/albums/listened/{album_id}` - Update an album

All GET endpoints remain public (no authentication required).

## How It Works

1. **Backend**: The FastAPI server checks for an `X-API-Key` header on write requests
2. **Frontend**: The `auth.js` script automatically adds the API key to write requests
3. **Storage**: The API key is stored in browser localStorage (only on your machine)

## Troubleshooting

### "API key required" error
- Make sure you've entered your API key when prompted
- Check that the API key in your `.env` file matches what you entered

### "Invalid API key" error
- Verify the API key in your `.env` file
- Clear localStorage and re-enter the key: `localStorage.removeItem('worldly_api_key')` in browser console

### Write operations still work without key
- Check that `API_KEY` is set in your `.env` file
- Restart the server after adding the key
- Check server logs for warnings about missing API_KEY

## Security Notes

- **Never commit your `.env` file** to version control
- Use a strong, random API key
- The API key is only stored in your browser's localStorage (local to your machine)
- For production, consider using more advanced authentication (OAuth, JWT tokens, etc.)

