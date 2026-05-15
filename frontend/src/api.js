export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const MEDIA_BASE_URL = import.meta.env.VITE_MEDIA_URL || 'http://localhost:8000';

const API_URL = API_BASE_URL;

export const loginUser = async (email, password) => {
    const response = await fetch(`${API_URL}/login/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: email, password: password })
    });
    if (!response.ok) {
        throw new Error('Login failed');
    }
    return response.json();
};

export const googleLoginUser = async (credential) => {
    const response = await fetch(`${API_URL}/google-login/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ credential })
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Google login failed');
    }
    return data;
};

export const getProfile = async (token) => {
    const response = await fetch(`${API_URL}/profile/`, {
        headers: {
            'Authorization': `Token ${token}`
        }
    });
    if (!response.ok) throw new Error('Failed to fetch profile');
    return response.json();
};

export const getPayslips = async (token) => {
    const response = await fetch(`${API_URL}/payslips/`, {
        headers: {
            'Authorization': `Token ${token}`
        }
    });
    if (!response.ok) throw new Error('Failed to fetch payslips');
    return response.json();
};

export const uploadDocument = async (token, formData) => {
    const response = await fetch(`${API_URL}/documents/`, {
        method: 'POST',
        headers: {
            'Authorization': `Token ${token}`
        },
        body: formData
    });
    if (!response.ok) throw new Error('Failed to upload document');
    return response.json();
};

export const getUserNotifications = async (token) => {
    const response = await fetch(`${API_URL}/user-notifications/`, {
        headers: {
            'Authorization': `Token ${token}`
        }
    });
    if (!response.ok) throw new Error('Failed to fetch notifications');
    return response.json();
};

export const markNotificationAsRead = async (token, notifId) => {
    const response = await fetch(`${API_URL}/user-notifications/${notifId}/`, {
        method: 'PATCH',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_read: true })
    });
    if (!response.ok) throw new Error('Failed to mark notification as read');
    return response.json();
};

export const updateProfile = async (token, data) => {
    const response = await fetch(`${API_URL}/profile/`, {
        method: 'PATCH',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update profile');
    return response.json();
};
