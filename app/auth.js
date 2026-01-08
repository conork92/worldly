// Authentication helper for API requests
// Handles login and API key management

(function() {
    'use strict';
    
    const API_KEY_STORAGE_KEY = 'worldly_api_key';
    const AUTH_STORAGE_KEY = 'worldly_auth';
    const LOGIN_USERNAME = 'conork';
    const LOGIN_PASSWORD = 'Password1';
    
    // Check if user is logged in
    function isLoggedIn() {
        return localStorage.getItem(AUTH_STORAGE_KEY) === 'true';
    }
    
    // Login function
    window.login = function(username, password) {
        if (username === LOGIN_USERNAME && password === LOGIN_PASSWORD) {
            localStorage.setItem(AUTH_STORAGE_KEY, 'true');
            return true;
        }
        return false;
    };
    
    // Logout function
    window.logout = function() {
        localStorage.removeItem(AUTH_STORAGE_KEY);
        localStorage.removeItem(API_KEY_STORAGE_KEY);
        location.reload();
    };
    
    // Get API key from localStorage or prompt user
    function getApiKey() {
        // Only prompt for API key if logged in
        if (!isLoggedIn()) {
            return null;
        }
        
        let apiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
        
        if (!apiKey) {
            // Prompt user to enter API key (only once)
            apiKey = prompt('Enter your API key to enable write operations:');
            if (apiKey) {
                localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
            } else {
                console.warn('API key not provided. Write operations will fail.');
            }
        }
        
        return apiKey;
    }
    
    // Helper function to add API key to fetch headers
    window.getAuthHeaders = function() {
        if (!isLoggedIn()) {
            return { 'Content-Type': 'application/json' };
        }
        
        const apiKey = getApiKey();
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
        
        const headers = getAuthHeaders();
        
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
    
    // Export login status check
    window.isLoggedIn = isLoggedIn;
})();

