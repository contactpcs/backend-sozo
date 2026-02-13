// Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';
const USERS_ENDPOINT = '/users';

// Role mapping from database role names to enum values for backend
const roleMapping = {
    'PATIENT_PORTAL': 'patient',
    'DOCTOR_UI': 'clinician',
    'CLINIC_ASSISTANT': 'nurse',
    'SUPER_ADMIN': 'admin',
    'PLATFORM_ADMIN': 'admin',
    'CLINICIAN_ADMIN': 'center_manager',
    'RECEPTIONIST': 'patient',  // map receptionist to patient for now
};

// DOM Elements
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const alertBox = document.getElementById('alert');
const responseBox = document.getElementById('responseBox');
const roleSelect = document.getElementById('registerRole');

// Fetch and load available roles
async function loadRoles() {
    try {
        const response = await fetch(`${API_BASE_URL}${USERS_ENDPOINT}/roles`);
        const data = await response.json();
        
        if (data.roles && data.roles.length > 0) {
            // Clear loading option
            roleSelect.innerHTML = '';
            
            // Add default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = '-- Select a role --';
            roleSelect.appendChild(defaultOption);
            
            // Add roles from database
            data.roles.forEach(role => {
                const option = document.createElement('option');
                option.value = role.role_name;  // Store role_name as value
                option.textContent = `${role.role_name}${role.description ? ' - ' + role.description : ''}`;
                roleSelect.appendChild(option);
            });
            
            // Set default to PATIENT_PORTAL if available
            roleSelect.value = 'PATIENT_PORTAL';
            
            console.log(`Loaded ${data.roles.length} roles`);
        }
    } catch (error) {
        console.error('Failed to load roles:', error);
        // Add static fallback options
        roleSelect.innerHTML = `
            <option value="">-- Select a role --</option>
            <option value="PATIENT_PORTAL" selected>Patient Portal</option>
            <option value="DOCTOR_UI">Doctor UI</option>
            <option value="CLINIC_ASSISTANT">Clinic Assistant</option>
            <option value="SUPER_ADMIN">Super Admin</option>
            <option value="CLINICIAN_ADMIN">Clinician Admin</option>
            <option value="RECEPTIONIST">Receptionist</option>
        `;
    }
}

// Tab switching functionality
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        
        // Remove active class from all tabs and contents
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding content
        btn.classList.add('active');
        document.getElementById(tabName).classList.add('active');
        
        // Load roles when switching to register tab
        if (tabName === 'register') {
            loadRoles();
        }
        
        // Clear previous responses
        clearAlert();
        responseBox.textContent = '';
    });
});

// Show alert message
function showAlert(message, type = 'info') {
    alertBox.textContent = message;
    alertBox.className = `alert show ${type}`;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        clearAlert();
    }, 5000);
}

// Clear alert message
function clearAlert() {
    alertBox.classList.remove('show');
}

// Display API response
function displayResponse(data, statusCode = 200) {
    responseBox.textContent = JSON.stringify(data, null, 2);
}

// Login handler
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        showAlert('Logging in...', 'info');
        
        const response = await fetch(`${API_BASE_URL}${USERS_ENDPOINT}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert('Login successful! Token saved.', 'success');
            displayResponse(data, response.status);
            
            // Save token to localStorage
            if (data.access_token) {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                localStorage.setItem('user_email', email);
            }
            
            // Clear form
            loginForm.reset();
        } else {
            showAlert(`Login failed: ${data.detail || 'Unknown error'}`, 'error');
            displayResponse(data, response.status);
        }
    } catch (error) {
        const errorMsg = error.message || 'Unknown error';
        showAlert(`Error: ${errorMsg}. Make sure backend is running on http://localhost:8000`, 'error');
        displayResponse({ 
            error: errorMsg,
            hint: 'Backend must be running on http://localhost:8000 with CORS enabled'
        });
    }
});

// Register handler
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('registerEmail').value;
    const firstName = document.getElementById('registerFirstName').value;
    const lastName = document.getElementById('registerLastName').value;
    const phone = document.getElementById('registerPhone').value;
    const password = document.getElementById('registerPassword').value;
    const selectedRoleName = document.getElementById('registerRole').value;
    
    // Validate password length
    if (password.length < 8) {
        showAlert('Password must be at least 8 characters long', 'error');
        return;
    }
    
    // Validate role selection
    if (!selectedRoleName) {
        showAlert('Please select a role', 'error');
        return;
    }
    
    // Map database role name to internal enum value
    const role = roleMapping[selectedRoleName] || 'patient';
    
    try {
        showAlert('Registering user...', 'info');
        
        const response = await fetch(`${API_BASE_URL}${USERS_ENDPOINT}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                first_name: firstName,
                last_name: lastName,
                phone: phone || null,
                password,
                role
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert('Registration successful! You can now login.', 'success');
            displayResponse(data, response.status);
            
            // Clear form
            registerForm.reset();
            
            // Reload roles dropdown
            roleSelect.value = 'PATIENT_PORTAL';
            
            // Switch to login tab after successful registration
            setTimeout(() => {
                document.querySelector('[data-tab="login"]').click();
            }, 2000);
        } else {
            showAlert(`Registration failed: ${data.detail || 'Unknown error'}`, 'error');
            displayResponse(data, response.status);
        }
    } catch (error) {
        const errorMsg = error.message || 'Unknown error';
        showAlert(`Error: ${errorMsg}. Make sure backend is running on http://localhost:8000`, 'error');
        displayResponse({ 
            error: errorMsg,
            hint: 'Backend must be running on http://localhost:8000 with CORS enabled'
        });
    }
});

// Check if user is logged in on page load
window.addEventListener('load', () => {
    const token = localStorage.getItem('access_token');
    const userEmail = localStorage.getItem('user_email');
    
    // Load roles for the registration form
    loadRoles();
    
    if (token && userEmail) {
        const message = `Previously logged in as: ${userEmail}`;
        showAlert(message, 'info');
    }
});

// Log out function (clear localStorage)
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_email');
    showAlert('Logged out successfully', 'success');
    loginForm.reset();
}

// Add logout button functionality (you can add a logout button in HTML)
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'l') {
        logout();
    }
});
