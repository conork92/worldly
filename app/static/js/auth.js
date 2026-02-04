// Authentication helper for API requests
// Handles login and API key management

(function() {
    'use strict';
    
    const API_KEY_STORAGE_KEY = 'worldly_api_key';
    const AUTH_STORAGE_KEY = 'worldly_auth';
    const USER_ROLE_KEY = 'worldly_user_role';
    
    // User credentials and roles
    const USERS = {
        'conork': {
            password: 'Password1',
            role: 'admin' // Can read and write
        },
        'guest': {
            password: 'WorldlyGuest',
            role: 'guest' // Can only read
        }
    };
    
    // Debug: Log available users on load
    console.log('Available users:', Object.keys(USERS));
    
    // Check if user is logged in
    function isLoggedIn() {
        return localStorage.getItem(AUTH_STORAGE_KEY) === 'true';
    }
    
    // Get current user role
    function getUserRole() {
        return localStorage.getItem(USER_ROLE_KEY) || null;
    }
    
    // Check if user can write (admin only)
    function canWrite() {
        return getUserRole() === 'admin';
    }
    
    // Login function
    window.login = function(username, password) {
        // Normalize username to lowercase for case-insensitive matching
        const normalizedUsername = (username || '').toLowerCase().trim();
        const normalizedPassword = (password || '').trim();
        
        console.log('Login attempt:', { 
            rawUsername: username, 
            normalizedUsername: normalizedUsername,
            passwordLength: normalizedPassword.length
        });
        
        const user = USERS[normalizedUsername];
        
        if (!user) {
            console.log('Login failed - User not found. Available users:', Object.keys(USERS));
            return false;
        }
        
        console.log('User found, checking password:', {
            expectedPassword: user.password,
            expectedLength: user.password.length,
            providedLength: normalizedPassword.length,
            match: user.password === normalizedPassword
        });
        
        if (user.password === normalizedPassword) {
            localStorage.setItem(AUTH_STORAGE_KEY, 'true');
            localStorage.setItem(USER_ROLE_KEY, user.role);
            console.log('Login successful:', { username: normalizedUsername, role: user.role });
            return true;
        }
        
        console.log('Login failed - Password mismatch');
        return false;
    };
    
    // Logout function
    window.logout = function() {
        localStorage.removeItem(AUTH_STORAGE_KEY);
        localStorage.removeItem(USER_ROLE_KEY);
        localStorage.removeItem(API_KEY_STORAGE_KEY);
        location.reload();
    };
    
    // Get API key from localStorage or prompt user
    async function getApiKey() {
        // Only prompt for API key if logged in
        if (!isLoggedIn()) {
            return null;
        }
        
        let apiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
        
        if (!apiKey) {
            // Check if API key is configured on the server
            try {
                const statusResponse = await fetch('/api/auth/status');
                const status = await statusResponse.json();
                
                if (!status.api_key_configured) {
                    alert('API key is not configured on the server. Please set API_KEY in your .env file and restart the server.');
                    return null;
                }
                
                // If API key is configured on server but not in localStorage,
                // check if we're in a production/deployed environment
                // In production (like Koyeb), skip the prompt
                const isProduction = window.location.hostname !== 'localhost' && 
                                    window.location.hostname !== '127.0.0.1' &&
                                    !window.location.hostname.startsWith('192.168.');
                
                if (isProduction && status.api_key_configured) {
                    // In production with server-side API key configured, skip the prompt
                    // The user can manually set it in localStorage if needed via browser console:
                    // localStorage.setItem('worldly_api_key', 'your-key-here')
                    console.log('API key configured on server. Skipping prompt in production environment.');
                    console.log('To enable write operations, set API key in browser console: localStorage.setItem("worldly_api_key", "your-key")');
                    return null; // Skip prompting in production
                }
            } catch (e) {
                console.warn('Could not check API key status:', e);
            }
            
            // Only prompt in development/local environments
            const promptMessage = 'Enter your API key to enable write operations.\n\n' +
                'This key should match the API_KEY value in your .env file.\n\n' +
                'If you don\'t have an API key set, add it to app/.env:\n' +
                'API_KEY=your-secret-key-here';
            
            apiKey = prompt(promptMessage);
            if (apiKey) {
                localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
            } else {
                console.warn('API key not provided. Write operations will fail.');
            }
        }
        
        return apiKey;
    }
    
    // Helper function to add API key to fetch headers
    window.getAuthHeaders = async function() {
        if (!isLoggedIn()) {
            return { 'Content-Type': 'application/json' };
        }
        
        const apiKey = await getApiKey();
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (apiKey) {
            headers['X-API-Key'] = apiKey;
        }
        
        return headers;
    };
    
    // Helper function to make authenticated fetch requests
    window.authenticatedFetch = async function(url, options = {}) {
        if (!isLoggedIn()) {
            throw new Error('You must be logged in to perform this action');
        }
        
        // Check if this is a write operation (POST, PATCH, PUT, DELETE)
        const isWriteOperation = ['POST', 'PATCH', 'PUT', 'DELETE'].includes((options.method || 'GET').toUpperCase());
        
        if (isWriteOperation && !canWrite()) {
            throw new Error('Guest users can only view data. Please log in as an admin to make changes.');
        }
        
        const headers = await getAuthHeaders();
        
        // Merge with existing headers
        options.headers = {
            ...headers,
            ...(options.headers || {})
        };
        
        const response = await fetch(url, options);
        
        // If unauthorized, clear stored key and prompt again
        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem(API_KEY_STORAGE_KEY);
            const newKey = prompt('API key invalid or expired. Enter a new API key:');
            if (newKey) {
                localStorage.setItem(API_KEY_STORAGE_KEY, newKey);
                // Retry the request
                options.headers['X-API-Key'] = newKey;
                return fetch(url, options);
            }
        }
        
        return response;
    };
    
    // Export functions
    window.isLoggedIn = isLoggedIn;
    window.getUserRole = getUserRole;
    window.canWrite = canWrite;
})();

