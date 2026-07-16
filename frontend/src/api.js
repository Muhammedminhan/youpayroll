const stripTrailingSlashes = (url) => url.replace(/\/+$/, '');

export const API_BASE_URL = stripTrailingSlashes(
    import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
);
export const MEDIA_BASE_URL = stripTrailingSlashes(
    import.meta.env.VITE_MEDIA_URL || 'http://localhost:8000'
);

const API_URL = API_BASE_URL;

// All requests include credentials so the HttpOnly auth_token cookie is sent automatically.
const defaultOptions = {
    credentials: 'include',
};

// Read the csrftoken cookie set by Django (it is NOT HttpOnly).
function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

// Returns extra headers needed for unsafe (state-changing) requests.
function csrfHeaders() {
    return { 'X-CSRFToken': getCsrfToken() };
}

// Fetch the CSRF cookie from the backend on app start so unsafe requests work.
export const bootstrapCsrf = () =>
    fetch(`${API_URL}/csrf/`, { ...defaultOptions }).catch(() => {});

export const googleLoginUser = async (credential) => {
    const response = await fetch(`${API_URL}/google-login/`, {
        ...defaultOptions,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...csrfHeaders() },
        body: JSON.stringify({ credential }),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Google login failed');
    }
    return response.json();
};

export const logoutUser = async () => {
    const response = await fetch(`${API_URL}/logout/`, {
        ...defaultOptions,
        method: 'POST',
        headers: { ...csrfHeaders() },
    });
    // 204 No Content on success; ignore non-ok (session may already be gone)
    return response.ok || response.status === 401;
};

export const getProfile = async () => {
    const response = await fetch(`${API_URL}/profile/`, defaultOptions);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to fetch profile');
    }
    return response.json();
};

export const getPayslips = async () => {
    const response = await fetch(`${API_URL}/payslips/`, defaultOptions);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to fetch payslips');
    }
    return response.json();
};

export const uploadDocument = async (formData) => {
    const response = await fetch(`${API_URL}/documents/`, {
        ...defaultOptions,
        method: 'POST',
        headers: { ...csrfHeaders() },
        body: formData,
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to upload document');
    }
    return response.json();
};

export const getUserNotifications = async () => {
    const response = await fetch(`${API_URL}/user-notifications/`, defaultOptions);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to fetch notifications');
    }
    return response.json();
};

export const markNotificationAsRead = async (notifId) => {
    const response = await fetch(`${API_URL}/user-notifications/${notifId}/`, {
        ...defaultOptions,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...csrfHeaders() },
        body: JSON.stringify({ is_read: true }),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to mark notification as read');
    }
    return response.json();
};

export const updateProfile = async (data) => {
    const response = await fetch(`${API_URL}/profile/`, {
        ...defaultOptions,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...csrfHeaders() },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Failed to update profile');
    }
    return response.json();
};
