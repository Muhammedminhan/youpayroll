import React, { useState, useEffect, useRef } from 'react';
import { User, Calendar, Mail, Briefcase, CreditCard, Files, Edit2, Moon, Sun, ChevronUp, ChevronDown, Building, LogOut, Check, X, Camera, Upload, Trash2, FileText, AlertCircle, ArrowRight, Crown, Clock, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { API_BASE_URL, MEDIA_BASE_URL } from '../api';
import ProfileImageModal from '../components/ProfileImageModal';
import ProfileInfoModal from '../components/ProfileInfoModal';
import LogoutModal from '../components/LogoutModal';
import { useNavigate, useLocation } from 'react-router-dom';

// --- SUB-COMPONENTS FOR NOTIFICATION WORKFLOW ---

const ActionRequiredModal = ({ isOpen, onClose, onUpload, onReject }) => {
    if (!isOpen) return null;
    const fileInputRef = useRef(null);
    const [selectedFile, setSelectedFile] = useState(null);

    return (
        <div className="modal-overlay">
            <div className="modal-content upload-modal pop-in">
                <button className="close-corner-btn" onClick={onClose}><X size={20} /></button>
                <div className="modal-header-section">
                    <h2 className="modal-title-v2">Action required!</h2>
                    <p className="modal-subtitle-v2">Kindly share the confirmation screenshot for the payment after updating your profile.</p>
                </div>

                <div className="upload-container-v2" onClick={() => fileInputRef.current.click()}>
                    <input type="file" ref={fileInputRef} onChange={(e) => setSelectedFile(e.target.files[0])} style={{ display: 'none' }} accept=".jpg,.png,.svg,.zip" />
                    <div className="upload-box-v2">
                        <div className="upload-icon-circle">
                            <Upload size={24} color="#B800C4" />
                        </div>
                        <div className="upload-text-group">
                            <span className="upload-main-text">Drag your file(s) to start uploading</span>
                            <span className="upload-divider-text">Or</span>
                            <button className="btn-browse-v2">Browse files</button>
                        </div>
                        <p className="upload-restrictions">Only support .jpg, .png and .svg and zip files</p>
                    </div>
                </div>

                {selectedFile && (
                    <div className="file-preview-card fade-in">
                        <div className="file-icon-box">
                            <FileText size={20} color="#B800C4" />
                        </div>
                        <div className="file-info">
                            <span className="file-name-text">{selectedFile.name}</span>
                            <span className="file-size-text">{(selectedFile.size / (1024 * 1024)).toFixed(1)}MB</span>
                        </div>
                        <button className="btn-remove-file" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}>
                            <X size={16} />
                        </button>
                    </div>
                )}

                <div className="modal-footer-v2">
                    <button className="btn-reject-link" onClick={onReject}>Reject modifications?</button>
                    <button
                        className="btn-acknowledge-solid"
                        onClick={() => onUpload(selectedFile)}
                    >
                        Acknowledge
                    </button>
                </div>
            </div>
            <style>{`
                .modal-header-section { margin-bottom: 2rem; text-align: left; }
                .modal-title-v2 { font-size: 1.8rem; font-weight: 800; color: #1e293b; margin-bottom: 0.75rem; }
                .modal-subtitle-v2 { color: #64748b; line-height: 1.6; font-size: 1.05rem; }

                .upload-container-v2 { cursor: pointer; margin-bottom: 1.5rem; }
                .upload-box-v2 { border: 2px dashed #e2e8f0; border-radius: 24px; padding: 3rem 2rem; text-align: center; background: #fcfaff; transition: border-color 0.2s; }
                .upload-box-v2:hover { border-color: #B800C4; }
                
                .upload-icon-circle { width: 56px; height: 56px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.5rem; box-shadow: 0 4px 12px rgba(184, 0, 196, 0.1); }
                .upload-text-group { display: flex; flex-direction: column; gap: 0.5rem; align-items: center; margin-bottom: 1.5rem; }
                .upload-main-text { font-weight: 700; color: #1e293b; font-size: 1.1rem; }
                .btn-browse-v2 { color: #B800C4; font-weight: 700; text-decoration: underline; background: none; border: none; cursor: pointer; padding: 0; }
                .upload-restrictions { font-size: 0.85rem; color: #94a3b8; }

                .file-preview-card { display: flex; align-items: center; gap: 1rem; padding: 1.25rem; background: white; border: 1px solid #f1f5f9; border-radius: 16px; margin-bottom: 2rem; }
                .file-icon-box { background: #fdf4ff; padding: 0.75rem; border-radius: 12px; }
                .file-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
                .file-name-text { font-weight: 700; color: #1e293b; font-size: 0.95rem; }
                .file-size-text { font-size: 0.8rem; color: #64748b; }
                
                .modal-footer-v2 { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 2rem; }
                .btn-reject-link { color: #B800C4; font-weight: 700; background: none; border: none; cursor: pointer; }
                .btn-acknowledge-solid { background: #B800C4; color: white; padding: 1rem 2.5rem; border-radius: 14px; font-weight: 700; border: none; cursor: pointer; }
                .btn-acknowledge-solid.disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }
            `}</style>
        </div>
    );
};

const RejectReasonModal = ({ isOpen, onClose, onSubmit }) => {
    if (!isOpen) return null;
    const [reason, setReason] = useState("");
    return (
        <div className="modal-overlay">
            <div className="modal-content reject-modal pop-in">
                <button className="close-corner-btn" onClick={onClose}><X size={20} /></button>

                <div className="modal-header-section" style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
                    <h2 className="modal-title-v2">Incorrect Modifications?</h2>
                    <p className="modal-subtitle-v2">Please specify the reason for rejection, and the admin will review and make the required changes.</p>
                </div>

                <div className="textarea-wrapper">
                    <textarea
                        className="premium-textarea"
                        placeholder="Type your reason here..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        maxLength={300}
                    />
                    <div className="char-counter">
                        <span className={reason.length === 300 ? 'at-limit' : ''}>{reason.length}</span>/300
                    </div>
                </div>

                <div className="modal-footer-v2" style={{ borderTop: 'none', padding: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <button onClick={onClose} className="btn-reject-cancel">Cancel</button>
                    <button
                        onClick={() => onSubmit(reason)}
                        className={`btn-reject-submit ${!reason.trim() ? 'disabled' : ''}`}
                        disabled={!reason.trim()}
                    >
                        Submit
                    </button>
                </div>
            </div>
            <style>{`
                .reject-modal { max-width: 520px !important; padding: 2.5rem 3rem !important; }
                .textarea-wrapper { position: relative; margin-bottom: 2rem; }
                .premium-textarea {
                    width: 100%;
                    height: 180px;
                    padding: 1.5rem;
                    border-radius: 24px;
                    border: 1.5px solid #e2e8f0;
                    background: #f8fafc;
                    font-family: inherit;
                    font-size: 1rem;
                    resize: none;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    color: #1e293b;
                }
                .premium-textarea:focus {
                    outline: none;
                    border-color: #B800C4;
                    background: white;
                    box-shadow: 0 0 0 4px rgba(184, 0, 196, 0.08);
                }
                .char-counter {
                    position: absolute;
                    bottom: 1.25rem;
                    right: 1.5rem;
                    font-size: 0.85rem;
                    font-weight: 700;
                    color: #94a3b8;
                }
                .at-limit { color: #ef4444; }

                .btn-reject-cancel {
                    background: white;
                    color: #64748b;
                    padding: 0.8rem 2.25rem;
                    border-radius: 16px;
                    font-weight: 700;
                    border: 1.5px solid #e2e8f0;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-size: 0.95rem;
                }
                .btn-reject-cancel:hover {
                    background: #fff1f2;
                    color: #ef4444;
                    border-color: #fecaca;
                }

                .btn-reject-submit {
                    background: #B800C4;
                    color: white;
                    padding: 0.8rem 2.5rem;
                    border-radius: 16px;
                    font-weight: 700;
                    border: none;
                    cursor: pointer;
                    font-size: 0.95rem;
                    transition: all 0.2s;
                    box-shadow: 0 4px 12px rgba(184, 0, 196, 0.2);
                }
                .btn-reject-submit:hover:not(.disabled) {
                    background: #a000aa;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 15px rgba(184, 0, 196, 0.3);
                }
                .btn-reject-submit.disabled {
                    background: #e2e8f0;
                    color: #94a3b8;
                    cursor: not-allowed;
                    box-shadow: none;
                }
            `}</style>
        </div>
    );
};

// --- MAIN PROFILE PAGE ---

const Profile = () => {
    const { user, login, logout, isDarkMode, toggleDarkMode } = useAuth();
    const { markAsRead, notifications } = useNotifications();
    const navigate = useNavigate();
    const location = useLocation();

    // Workflow State
    const [isFromNotification, setIsFromNotification] = useState(!!location.state?.triggerAction);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    const [showRejectPopup, setShowRejectPopup] = useState(false);
    const [notifId, setNotifId] = useState(location.state?.notificationId);

    // Modal States
    const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
    const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
    const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

    // Data State
    const [formData, setFormData] = useState({
        first_name: '', last_name: '', designation: '', consultant_id: '', gender: '', dob: '', email: '',
        contract_start: '', contract_end: '', consultant_fee: '', reporting_to_name: '', reporting_to_role: '',
        account_number: '', ifsc_code: '', micr_code: '', branch_address: '',
    });

    const [profileImage, setProfileImage] = useState(user?.avatar || `https://ui-avatars.com/api/?name=${user?.name || 'User'}&background=B800C4&color=fff&size=128`);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (user) {
            const [firstName, ...lastNameParts] = (user.name || '').split(' ');
            setFormData({
                first_name: firstName || '', last_name: lastNameParts.join(' ') || '', designation: user.role || '',
                consultant_id: user.consultantId || '', gender: user.gender || '', dob: user.dob || '', email: user.email || '',
                contract_start: user.contractStart || '', contract_end: user.contractEnd || '', consultant_fee: user.consultantFee || '0',
                reporting_to_name: user.reporting_to_name || user.reportingTo?.name || '', reporting_to_role: user.reporting_to_role || user.reportingTo?.role || '',
                account_number: user.bankDetails?.accountNumber || '', ifsc_code: user.bankDetails?.ifscCode || '',
                micr_code: user.bankDetails?.micrCode || '', branch_address: user.bankDetails?.branchAddress || '',
            });
            // Update the profile image state whenever the user object changes
            setProfileImage(user.avatar);
        }
    }, [user]);

    const getCsrfToken = () => {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    };

    const handleSaveProfile = async (updatedData) => {
        setIsSaving(true);
        try {
            const response = await fetch(`${API_BASE_URL}/profile/`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify(updatedData)
            });
            if (response.ok) {
                await login(user.email);
                setIsInfoModalOpen(false);
            }
        } catch (err) { console.error(err); } finally { setIsSaving(false); }
    };

    const handleRemoveAvatar = async () => {
        setIsSaving(true);
        try {
            const response = await fetch(`${API_BASE_URL}/profile/`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ profile_picture: null })
            });

            if (response.ok) {
                // Force an immediate refresh of the user context
                await login(user.email);
                // Also clear the local image state manually to be sure the UI updates
                const initialsUrl = `https://ui-avatars.com/api/?name=${user?.name || 'User'}&background=B800C4&color=fff&size=128&v=${Date.now()}`;
                setProfileImage(initialsUrl);
            }
        } catch (err) { console.error(err); } finally { setIsSaving(false); }
    };

    const handleSaveAvatar = async (imageData) => {
        setIsSaving(true);
        try {
            const response = await fetch(`${API_BASE_URL}/profile/`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ profile_picture: imageData })
            });

            if (response.ok) {
                await login(user.email);
            }
        } catch (err) { console.error(err); } finally { setIsSaving(false); }
    };

    const handleNotificationAcknowledge = async (file) => {
        let idToMark = notifId;

        // If no notifId in state (e.g. refresh), try to find an unread ACTION_REQUIRED one
        if (!idToMark) {
            const unreadActionNotif = (notifications || []).find(n => n.notification_type === 'ACTION_REQUIRED' && !n.is_read);
            if (unreadActionNotif) {
                idToMark = unreadActionNotif.id;
            }
        }

        if (idToMark) {
            await markAsRead(idToMark);
        }

        setShowConfirmPopup(false);
        setIsFromNotification(false);
        navigate('/', { state: { success: true } });
    };

    const handleNotificationReject = async (reason) => {
        if (notifId) {
            await markAsRead(notifId);
        }
        setShowRejectPopup(false);
        setIsFromNotification(false);
        navigate('/', { state: { success: true, message: "Modifications rejected. Admin will be notified." } });
    };

    return (
        <div className={`profile-page ${isDarkMode ? 'dark' : ''}`}>
            {isFromNotification && (
                <div className="workflow-banner fade-in">
                    <div className="banner-text">
                        <AlertCircle size={20} color="#B800C4" />
                        <span>Please review your profile details below. If everything is correct, click to finalize.</span>
                    </div>
                    <div className="banner-actions">
                        <button className="btn-workflow-primary" onClick={() => setShowConfirmPopup(true)}>
                            <span>Confirm & Acknowledge</span>
                            <ArrowRight size={18} />
                        </button>
                        <button className="btn-workflow-secondary" onClick={() => setShowRejectPopup(true)}>Reject</button>
                    </div>
                </div>
            )}

            <header className="page-header-v4">
                <div className="title-nav">
                    <span className="nav-label">Profile</span>
                    <div className="theme-toggle-switch" onClick={toggleDarkMode}>
                        <div className={`switch-ball ${isDarkMode ? 'dark' : ''}`}>
                            {isDarkMode ? <Moon size={12} color="#B800C4" /> : <Sun size={12} color="#B800C4" />}
                        </div>
                    </div>
                </div>
            </header>

            <div className="profile-hero-section">
                <div className="avatar-wrapper-v4">
                    <div className="avatar-circle-v4">
                        <img src={profileImage} alt="Profile" className="avatar-img-v4" />
                        <button className="avatar-edit-pencil" onClick={() => setIsProfileModalOpen(true)}>
                            <Edit2 size={14} color="white" />
                        </button>
                    </div>
                    <h2 className="hero-name">{user?.name || 'User'}</h2>
                    <p className="hero-role">{user?.role || 'Consultant'}</p>
                </div>
            </div>

            <div className="profile-details-grid">
                <div className="info-card-v4">
                    <div className="card-header-v4">
                        <h3>Your Info</h3>
                        <button className="btn-edit-link" onClick={() => setIsInfoModalOpen(true)}>Edit Profile</button>
                    </div>
                    <div className="info-items-v4">
                        <div className="info-row-v4">
                            <div className="row-label"><Crown size={18} /><span>Consultant ID</span></div>
                            <span className="row-value">{formData.consultant_id || 'N/A'}</span>
                        </div>
                        <div className="info-row-v4">
                            <div className="row-label"><User size={18} /><span>Gender</span></div>
                            <span className="row-value">{formData.gender || 'N/A'}</span>
                        </div>
                        <div className="info-row-v4">
                            <div className="row-label"><Calendar size={18} /><span>Date Of Birth</span></div>
                            <span className="row-value">{formData.dob || 'N/A'}</span>
                        </div>
                        <div className="info-row-v4">
                            <div className="row-label"><Mail size={18} /><span>Email</span></div>
                            <span className="row-value-email">{formData.email}</span>
                        </div>
                        <div className="info-row-v4">
                            <div className="row-label"><Briefcase size={18} /><span>Contract Period</span></div>
                            <span className="row-value">{formData.contract_start} to {formData.contract_end}</span>
                        </div>
                    </div>

                    <div className="reporting-footer-v4">
                        <div className="reporting-label"><User size={18} color="#94a3b8" /><span>Reporting to</span></div>
                        <span className="reporting-value">{user?.reportingTo?.name || 'Not Managed'} - {user?.reportingTo?.role || ''}</span>
                    </div>
                </div>

                <div className="bank-section-v4">
                    <div className="section-header-v4">
                        <h3>Your Bank Details</h3>
                        <div className="toggle-indicator-circle">
                            <ChevronDown size={14} />
                        </div>
                    </div>

                    <div className="bank-card-v4">
                        <div className="bank-card-main">
                            <div className="card-top-row">
                                <div className="field-group">
                                    <span className="f-label">ACCOUNT NO</span>
                                    <span className="f-value">{formData.account_number || '73030100178'}</span>
                                </div>
                                <div className="chip-icon">
                                    <svg width="36" height="26" viewBox="0 0 40 30" fill="none">
                                        <rect width="40" height="30" rx="6" fill="var(--text-secondary)" opacity="0.2" />
                                        <path d="M8 8H18M8 15H18M8 22H18M26 8H32V22H26V8Z" stroke="var(--text-secondary)" strokeWidth="1.5" opacity="0.4" />
                                    </svg>
                                </div>
                            </div>

                            <div className="card-mid-row">
                                <div className="field-group">
                                    <span className="f-label">IFSC CODE</span>
                                    <span className="f-value-small">{formData.ifsc_code || 'ICIC0007'}</span>
                                </div>
                                <div className="field-group align-right">
                                    <span className="f-label">MICR CODE</span>
                                    <span className="f-value-small">{formData.micr_code || '673220'}</span>
                                </div>
                            </div>

                            <div className="card-bottom-row">
                                <span className="owner-name">{(user?.name || "PAUL BARBER").toUpperCase()}</span>
                                <div className="mastercard-logo">
                                    <div className="mc-circle mc-red"></div>
                                    <div className="mc-circle mc-orange"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="branch-footer-v4">
                        {formData.branch_address || 'ICICI BANK LTD, GROUND FLOOR, INFOPRADE, KERALA-673220'}
                    </div>
                </div>

                {/* Mobile-only menu items */}
                <div className="mobile-only-menu">
                    <div className="menu-list-card">
                        <div className="menu-list-item" onClick={toggleDarkMode}>
                            <div className="item-left">
                                <div className="icon-box-v4">
                                    {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                                </div>
                                <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
                            </div>
                            <div className="item-right">
                                <div className={`theme-switch-pill ${isDarkMode ? 'dark' : ''}`}>
                                    <div className="pill-ball"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <button className="mobile-logout-btn" onClick={() => setIsLogoutModalOpen(true)}>
                        <span>Logout</span>
                    </button>
                </div>
            </div>

            {/* Workflow Modals */}
            <ActionRequiredModal
                isOpen={showConfirmPopup}
                onClose={() => setShowConfirmPopup(false)}
                onUpload={handleNotificationAcknowledge}
                onReject={() => { setShowConfirmPopup(false); setShowRejectPopup(true); }}
            />
            <RejectReasonModal isOpen={showRejectPopup} onClose={() => setShowRejectPopup(false)} onSubmit={handleNotificationReject} />

            <ProfileInfoModal
                isOpen={isInfoModalOpen}
                onClose={() => setIsInfoModalOpen(false)}
                formData={formData}
                onSave={handleSaveProfile}
                isSaving={isSaving}
            />

            <ProfileImageModal
                isOpen={isProfileModalOpen}
                currentImage={profileImage}
                onClose={() => setIsProfileModalOpen(false)}
                onSave={handleSaveAvatar}
                onRemove={handleRemoveAvatar}
            />
            <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} onConfirm={() => { logout(); navigate('/login'); }} />

            <style>{`
                .profile-page { max-width: 1000px; margin: 0 auto; padding: 1.5rem; position: relative; min-height: 100vh; padding-bottom: 5rem; }
                
                .mobile-only-menu { display: none; flex-direction: column; gap: 1.5rem; margin-top: 1rem; }
                
                @media (max-width: 768px) {
                    .profile-page { padding: 1.25rem; }
                    .mobile-only-menu { display: flex; margin-bottom: 2rem; }
                    .page-header-v4 { display: none !important; }
                    .profile-hero-section { margin-bottom: 2rem; }
                    .avatar-circle-v4 { width: 100px; height: 100px; margin-bottom: 1rem; }
                    .hero-name { font-size: 1.4rem; font-weight: 800; }
                    .hero-role { font-size: 0.9rem; }
                    .info-card-v4, .bank-section-v4 { padding: 1.25rem; border-radius: 20px; }
                    .card-header-v4 { margin-bottom: 1.25rem; }
                    .card-header-v4 h3 { font-size: 1rem; }
                    .info-items-v4 { gap: 1rem; margin-bottom: 1.25rem; }
                    .row-label { font-size: 0.85rem; gap: 0.6rem; }
                    .row-value, .row-value-email { font-size: 0.85rem; }
                    .bank-card-v4 { padding: 1.1rem; border-radius: 18px; }
                    .f-label { font-size: 0.55rem; }
                    .f-value { font-size: 1rem; }
                    .f-value-small, .owner-name { font-size: 0.9rem; }
                }

                .menu-list-card { background: var(--card-bg); border-radius: 24px; border: 1px solid var(--border-color); padding: 0.5rem; }
                .menu-list-item { display: flex; justify-content: space-between; align-items: center; padding: 1rem; cursor: pointer; border-radius: 18px; transition: background 0.2s; }
                .menu-list-item:hover { background: var(--bg-color); }
                
                .item-left { display: flex; align-items: center; gap: 1rem; }
                .item-left span { font-weight: 700; color: var(--text-primary); font-size: 0.95rem; }
                .icon-box-v4 { width: 40px; height: 40px; border-radius: 12px; background: var(--bg-color); display: flex; align-items: center; justify-content: center; color: #B800C4; }
                
                .theme-switch-pill { width: 46px; height: 24px; background: var(--border-color); border-radius: 12px; position: relative; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
                .theme-switch-pill.dark { background: #B800C4; }
                .pill-ball { position: absolute; left: 3px; top: 3px; width: 18px; height: 18px; background: white; border-radius: 50%; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .theme-switch-pill.dark .pill-ball { left: 25px; }

                .mobile-logout-btn { background: none; border: none; padding: 1.25rem; width: 100%; border-radius: 20px; color: #ef4444; font-weight: 800; font-size: 1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; margin-bottom: 2rem; transition: background 0.2s; }
                .mobile-logout-btn:hover { background: #fef2f2; }
                body.dark-mode .mobile-logout-btn:hover { background: rgba(239, 68, 68, 0.1); }

                /* V4 Header & Toggle */
                .page-header-v4 { display: flex; justify-content: flex-end; margin-bottom: 2rem; }
                .title-nav { display: flex; align-items: center; gap: 1rem; }
                .nav-label { font-weight: 700; color: var(--text-secondary); font-size: 0.9rem; }
                .theme-toggle-switch { width: 44px; height: 24px; background: var(--border-color); border-radius: 20px; padding: 2px; cursor: pointer; position: relative; transition: background 0.3s; }
                .switch-ball { width: 20px; height: 20px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
                .switch-ball.dark { transform: translateX(20px); }

                /* Hero Section */
                .profile-hero-section { text-align: center; margin-bottom: 4rem; }
                .avatar-wrapper-v4 { display: flex; flex-direction: column; align-items: center; }
                .avatar-circle-v4 { position: relative; width: 140px; height: 140px; margin-bottom: 1.5rem; }
                .avatar-img-v4 { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 4px solid var(--card-bg); box-shadow: 0 10px 25px var(--shadow-color); }
                .avatar-edit-pencil { position: absolute; bottom: 8px; right: 8px; background: #B800C4; width: 28px; height: 28px; border-radius: 50%; border: 3px solid var(--card-bg); display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
                .hero-name { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.25rem; }
                .hero-role { color: var(--text-secondary); font-weight: 600; font-size: 1.05rem; }

                /* Details Page */
                .profile-details-grid { display: flex; flex-direction: column; gap: 2rem; max-width: 600px; margin: 0 auto; }

                .info-card-v4 { background: var(--card-bg); border-radius: 32px; padding: 2rem; box-shadow: 0 4px 30px var(--shadow-color); border: 1px solid var(--border-color); }
                .card-header-v4 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
                .card-header-v4 h3 { font-size: 1.25rem; font-weight: 800; color: var(--text-primary); }
                .btn-edit-link { color: #B800C4; font-weight: 700; background: none; border: none; cursor: pointer; font-size: 0.9rem; text-decoration: underline; }
                
                .info-items-v4 { display: flex; flex-direction: column; gap: 1.5rem; margin-bottom: 2rem; }
                .info-row-v4 { display: flex; justify-content: space-between; align-items: center; }
                .row-label { display: flex; align-items: center; gap: 1rem; color: var(--text-secondary); font-weight: 600; font-size: 1rem; }
                .row-label i, .row-label svg { color: var(--text-secondary); opacity: 0.5; }
                .row-value { font-weight: 700; color: var(--text-primary); font-size: 1rem; }
                .row-value-email { font-weight: 700; color: #B800C4; font-size: 1rem; text-decoration: underline; }

                .reporting-footer-v4 { padding-top: 1.5rem; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
                .reporting-label { display: flex; align-items: center; gap: 0.75rem; color: var(--text-secondary); font-weight: 700; font-size: 0.9rem; text-transform: uppercase; }
                .reporting-value { font-weight: 700; color: var(--text-secondary); font-size: 0.95rem; }

                /* Bank Section V4 */
                .bank-section-v4 { background: var(--card-bg); border-radius: 32px; padding: 2rem; box-shadow: 0 4px 30px var(--shadow-color); border: 1px solid var(--border-color); }
                .section-header-v4 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
                .section-header-v4 h3 { font-size: 1.25rem; font-weight: 800; color: var(--text-primary); }
                .toggle-indicator-circle { width: 28px; height: 28px; border: 1.5px solid var(--border-color); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #B800C4; }

                .bank-card-v4 { background: var(--bg-color); border-radius: 24px; padding: 2rem; border: 1px solid var(--border-color); }
                .bank-card-main { display: flex; flex-direction: column; gap: 2rem; }
                .card-top-row, .card-mid-row, .card-bottom-row { display: flex; justify-content: space-between; align-items: center; }
                
                .field-group { display: flex; flex-direction: column; gap: 4px; }
                .align-right { text-align: right; }
                .f-label { font-size: 0.7rem; color: var(--text-secondary); font-weight: 600; letter-spacing: 0.05em; }
                .f-value { font-size: 1.4rem; font-weight: 800; color: var(--text-primary); letter-spacing: 1px; }
                .f-value-small { font-size: 1.2rem; font-weight: 800; color: var(--text-primary); }
                .owner-name { font-size: 1.25rem; font-weight: 800; color: var(--text-primary); }

                .mastercard-logo { display: flex; }
                .mc-circle { width: 28px; height: 28px; border-radius: 50%; }
                .mc-red { background: #eb001b; z-index: 1; }
                .mc-orange { background: #ff5f00; margin-left: -14px; opacity: 0.8; }

                .branch-footer-v4 { margin-top: 1.5rem; color: var(--text-secondary); font-size: 0.85rem; text-align: center; font-weight: 500; line-height: 1.4; }

                /* Banner */
                .workflow-banner { 
                    background: #fdf4ff; 
                    border: 1px solid #fce7f3; 
                    border-radius: 20px; 
                    padding: 1rem 1.5rem; 
                    display: flex; 
                    align-items: center; 
                    justify-content: space-between; 
                    margin-bottom: 2.5rem; 
                    box-shadow: 0 4px 20px rgba(184, 0, 196, 0.08); 
                }
                body.dark-mode .workflow-banner {
                    background: rgba(184, 0, 196, 0.05);
                    border-color: rgba(184, 0, 196, 0.2);
                }
                .banner-text { display: flex; align-items: center; gap: 0.75rem; color: var(--text-primary); font-weight: 600; font-size: 0.95rem; }
                .banner-actions { display: flex; align-items: center; gap: 0.75rem; }

                .btn-workflow-primary {
                    background: #B800C4;
                    color: white;
                    padding: 0.65rem 1.5rem;
                    border-radius: 14px;
                    font-weight: 700;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 4px 12px rgba(184, 0, 196, 0.2);
                    font-size: 0.9rem;
                }
                .btn-workflow-primary:hover {
                    background: #a000aa;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 15px rgba(184, 0, 196, 0.3);
                }
                .btn-workflow-secondary {
                    background: white;
                    color: #64748b;
                    padding: 0.65rem 1.5rem;
                    border-radius: 14px;
                    font-weight: 700;
                    border: 1px solid #e2e8f0;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-size: 0.9rem;
                }
                body.dark-mode .btn-workflow-secondary {
                    background: var(--card-bg);
                    border-color: var(--border-color);
                    color: var(--text-secondary);
                }
                .btn-workflow-secondary:hover {
                    background: #fff1f2;
                    color: #ef4444;
                    border-color: #fecaca;
                }
                body.dark-mode .btn-workflow-secondary:hover {
                    background: rgba(239, 68, 68, 0.1);
                }

                .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 6000; padding: 1.5rem; }
                .modal-content { max-width: 550px; width: 100%; padding: 3rem; border-radius: 32px; background: white; position: relative; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
                .close-corner-btn { position: absolute; top: 1.5rem; right: 1.5rem; color: #94a3b8; background: #f8fafc; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; cursor: pointer; }

                .pop-in { animation: popIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
                @keyframes popIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
                .fade-in { animation: fadeIn 0.4s ease-out; }
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            `}</style>
        </div>
    );
};

export default Profile;
