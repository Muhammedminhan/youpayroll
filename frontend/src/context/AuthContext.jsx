import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { MEDIA_BASE_URL, googleLoginUser, getProfile, logoutUser } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(localStorage.getItem('theme') === 'dark');

    const clearLocalAuth = useCallback(() => {
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('user');
    }, []);

    const logout = useCallback(async () => {
        try {
            await logoutUser();
        } catch (_) {
            // best-effort — clear local state regardless
        }
        clearLocalAuth();
    }, [clearLocalAuth]);

    const updateUserData = useCallback((profileData) => {
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
                role: profileData.reporting_to_role,
            },
            bankDetails: {
                accountNumber: profileData.account_number,
                ifscCode: profileData.ifsc_code,
                micrCode: profileData.micr_code,
                branch_address: profileData.branch_address,
            },
        };
        setUser(userObj);
        setIsAuthenticated(true);
        localStorage.setItem('user', JSON.stringify(userObj));
    }, []);

    const syncProfile = useCallback(async () => {
        try {
            const profileData = await getProfile();
            updateUserData(profileData);
            return true;
        } catch (error) {
            console.error('Profile sync error:', error);
            return false;
        }
    }, [updateUserData]);

    const login = async (_email, credential = null) => {
        try {
            let authData;
            if (credential) {
                authData = await googleLoginUser(credential);
            } else {
                throw new Error('Google sign-in is required.');
            }
            // Token is delivered as an HttpOnly cookie — no localStorage storage needed.
            updateUserData(authData);
            return { success: true };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    };

    useEffect(() => {
        const initializeAuth = async () => {
            try {
                const storedUser = localStorage.getItem('user');
                if (storedUser) {
                    try {
                        const parsedUser = JSON.parse(storedUser);
                        setUser(parsedUser);
                        setIsAuthenticated(true);
                        // Validate session is still alive (cookie present + not expired)
                        const ok = await syncProfile();
                        if (!ok) clearLocalAuth();
                    } catch (err) {
                        console.error('Failed to parse or sync user:', err);
                        clearLocalAuth();
                    }
                }

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
    }, [isDarkMode, syncProfile, clearLocalAuth]);

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

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, login, logout, loading, isDarkMode, toggleDarkMode }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
