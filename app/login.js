// Login UI and management

(function() {
    'use strict';
    
    // Create login modal HTML
    function createLoginModal() {
        const overlay = document.createElement('div');
        overlay.className = 'login-overlay';
        overlay.id = 'login-overlay';
        overlay.innerHTML = `
            <div class="login-modal">
                <h2>Login Required</h2>
                <form id="login-form">
                    <div class="login-form-group">
                        <label for="login-username">Username</label>
                        <input type="text" id="login-username" name="username" placeholder="Enter username" required autocomplete="username">
                    </div>
                    <div class="login-form-group">
                        <label for="login-password">Password</label>
                        <input type="password" id="login-password" name="password" placeholder="Enter password" required autocomplete="current-password">
                    </div>
                    <div class="login-error" id="login-error"></div>
                    <button type="submit" class="login-button">Login</button>
                </form>
            </div>
        `;
        return overlay;
    }
    
    // Create logout button
    function createLogoutButton() {
        const button = document.createElement('button');
        button.className = 'logout-button';
        button.id = 'logout-button';
        button.textContent = 'Logout';
        button.onclick = function() {
            if (confirm('Are you sure you want to logout?')) {
                logout();
            }
        };
        return button;
    }
    
    // Show login modal
    function showLoginModal() {
        let overlay = document.getElementById('login-overlay');
        if (!overlay) {
            overlay = createLoginModal();
            document.body.appendChild(overlay);
            
            // Handle form submission
            const form = document.getElementById('login-form');
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const username = document.getElementById('login-username').value;
                const password = document.getElementById('login-password').value;
                const errorDiv = document.getElementById('login-error');
                
                if (window.login(username, password)) {
                    overlay.classList.add('login-hidden');
                    showLogoutButton();
                    // Trigger custom event for pages to react to login
                    window.dispatchEvent(new CustomEvent('userLoggedIn'));
                } else {
                    errorDiv.textContent = 'Invalid username or password';
                    document.getElementById('login-password').value = '';
                }
            });
        }
        overlay.classList.remove('login-hidden');
    }
    
    // Hide login modal
    function hideLoginModal() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) {
            overlay.classList.add('login-hidden');
        }
    }
    
    // Show logout button
    function showLogoutButton() {
        let button = document.getElementById('logout-button');
        if (!button) {
            button = createLogoutButton();
            document.body.appendChild(button);
        }
        button.style.display = 'block';
    }
    
    // Hide logout button
    function hideLogoutButton() {
        const button = document.getElementById('logout-button');
        if (button) {
            button.style.display = 'none';
        }
    }
    
    // Check login status and show/hide UI accordingly
    function checkLoginStatus() {
        if (window.isLoggedIn && window.isLoggedIn()) {
            hideLoginModal();
            showLogoutButton();
        } else {
            showLoginModal();
            hideLogoutButton();
        }
    }
    
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkLoginStatus);
    } else {
        checkLoginStatus();
    }
    
    // Listen for login events
    window.addEventListener('userLoggedIn', function() {
        checkLoginStatus();
        // Show/hide write forms based on login status
        updateWriteFormsVisibility();
    });
    
    // Update visibility of write forms based on login status and permissions
    function updateWriteFormsVisibility() {
        const isLoggedIn = window.isLoggedIn && window.isLoggedIn();
        const canWrite = window.canWrite && window.canWrite();
        const userRole = window.getUserRole && window.getUserRole();
        
        // Hide/show add quote button and form
        const addQuoteBtn = document.getElementById('toggle-form-btn');
        const addQuoteForm = document.getElementById('add-quote-form-container');
        if (addQuoteBtn) addQuoteBtn.style.display = canWrite ? 'block' : 'none';
        if (addQuoteForm && !canWrite) {
            addQuoteForm.style.display = 'none';
        }
        
        // Hide/show assign country button and form (books page)
        const assignBtn = document.getElementById('toggle-assign-btn');
        const assignForm = document.getElementById('assign-country-form');
        if (assignBtn) assignBtn.style.display = canWrite ? 'block' : 'none';
        if (assignForm && !canWrite) {
            assignForm.style.display = 'none';
        }
        
        // Hide/show add artist button (country page)
        const addArtistBtn = document.getElementById('toggle-artist-form-btn');
        if (addArtistBtn) addArtistBtn.style.display = canWrite ? 'block' : 'none';
        
        // Hide/show refresh button (listening page)
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) refreshBtn.style.display = canWrite ? 'block' : 'none';
        
        // Update logout button to show user role
        const logoutBtn = document.getElementById('logout-button');
        if (logoutBtn && isLoggedIn) {
            const roleText = userRole === 'admin' ? 'Admin' : 'Guest';
            logoutBtn.textContent = `Logout (${roleText})`;
        }
        
        // Albums edit forms are handled by click handlers, but we can disable them
        // The authenticatedFetch will throw an error if not logged in or guest user
    }
    
    // Call on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateWriteFormsVisibility);
    } else {
        setTimeout(updateWriteFormsVisibility, 100); // Small delay to ensure DOM is ready
    }
    
    // Export functions
    window.showLoginModal = showLoginModal;
    window.hideLoginModal = hideLoginModal;
    window.updateWriteFormsVisibility = updateWriteFormsVisibility;
})();

