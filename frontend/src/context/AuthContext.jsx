import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE_URL, MEDIA_BASE_URL, loginUser, googleLoginUser, getProfile } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(localStorage.getItem('theme') === 'dark');

    useEffect(() => {
        const initializeAuth = async () => {
            try {
                const storedUser = localStorage.getItem('user');
                if (storedUser) {
                    try {
                        const parsedUser = JSON.parse(storedUser);
                        setUser(parsedUser);
                        setIsAuthenticated(true);

                        // Background sync with backend
                        const token = localStorage.getItem('token');
                        if (token) {
                            await syncProfile(token);
                        }
                    } catch (err) {
                        console.error('Failed to parse or sync user:', err);
                        // Clear corrupted state
                        logout();
                    }
                }

                // Initial Theme Apply
                if (isDarkMode) {
                    document.body.classList.add('dark-mode');
                } else {
                    document.body.classList.remove('dark-mode');
                }
            } finally {
                setLoading(false);
            }
        };

        initializeAuth();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const toggleDarkMode = () => {
        const newMode = !isDarkMode;
        setIsDarkMode(newMode);
        localStorage.setItem('theme', newMode ? 'dark' : 'light');
        if (newMode) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    };

    const syncProfile = async (token) => {
        try {
            const profileData = await getProfile(token);
            updateUserData(profileData, token);
            return true;
        } catch (error) {
            console.error('Profile sync error:', error);
            return false;
        }
    };

    const updateUserData = (profileData, token) => {
        // Construct full URL for profile picture
        let avatarUrl = profileData.profile_picture;
        if (avatarUrl && !avatarUrl.startsWith('http')) {
            avatarUrl = `${MEDIA_BASE_URL}${avatarUrl}`;
        }

        const firstName = profileData.user?.first_name || '';
        const lastName = profileData.user?.last_name || '';
        const fullName = `${firstName} ${lastName}`.trim();

        const userObj = {
            email: profileData.user?.email,
            name: fullName || profileData.user?.username || 'User',
            role: profileData.designation || 'Consultant',
            avatar: avatarUrl || `https://ui-avatars.com/api/?name=${firstName || 'User'}+${lastName}&background=B800C4&color=fff`,
            consultantId: profileData.consultant_id,
            gender: profileData.gender,
            dob: profileData.dob,
            contractStart: profileData.contract_start,
            contractEnd: profileData.contract_end,
            consultantFee: profileData.consultant_fee,
            reportingTo: {
                name: profileData.reporting_to_name,
                role: profileData.reporting_to_role
            },
            bankDetails: {
                accountNumber: profileData.account_number,
                ifscCode: profileData.ifsc_code,
                micrCode: profileData.micr_code,
                branch_address: profileData.branch_address
            }
        };
        setUser(userObj);
        setIsAuthenticated(true);
        localStorage.setItem('user', JSON.stringify(userObj));
        if (token) {
            localStorage.setItem('token', token);
        }
    }

    const login = async (email, credential = null) => {
        try {
            let authData;
            if (credential) {
                authData = await googleLoginUser(credential);
            } else {
                // Regular login - though not currently used in this flow
                authData = await loginUser(email, '');
            }

            if (authData.token) {
                updateUserData(authData, authData.token);
                return { success: true };
            }
            return { success: false, error: 'Token missing in response' };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    };

    const logout = () => {
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('user');
        localStorage.removeItem('token');
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, login, logout, loading, isDarkMode, toggleDarkMode }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
