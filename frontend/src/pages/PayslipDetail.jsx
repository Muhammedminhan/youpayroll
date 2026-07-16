import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, ChevronDown, Download, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL, MEDIA_BASE_URL } from '../api';

const PayslipDetail = () => {
    const navigate = useNavigate();
    const { month } = useParams();
    const { user } = useAuth();
    const [selectedMonth, setSelectedMonth] = useState(month || 'March');
    const [showSalary, setShowSalary] = useState(false);
    const [loading, setLoading] = useState(true);
    const [payslip, setPayslip] = useState(null);

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    useEffect(() => {
        fetchPayslipDetail();
    }, [selectedMonth]);

    const fetchPayslipDetail = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/payslips/?month=${selectedMonth}`, {
                credentials: 'include',
            });
            if (response.ok) {
                const data = await response.json();
                if (data.length > 0) {
                    setPayslip(data[0]);
                } else {
                    // Mock data if no real data
                    setPayslip({
                        month: selectedMonth,
                        gross_pay: 2602.0,
                        reimbursement: 1602.0,
                        deductions: 0.0,
                        take_home: 80.0,
                        file: '#',
                        tax_worksheet: '#'
                    });
                }
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const formatCurrency = (value) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    };

    const handleDownload = async () => {
        if (!payslip || !payslip.file || payslip.file === '#') {
            alert('File not available for this record.');
            return;
        }

        const baseUrl = MEDIA_BASE_URL;
        const fullUrl = payslip.file.startsWith('http') ? payslip.file : `${baseUrl}${payslip.file}`;

        try {
            const response = await fetch(fullUrl, { credentials: 'include' });

            if (!response.ok) throw new Error('Download failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Payslip_${selectedMonth}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading document:', error);
            window.open(fullUrl, '_blank');
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <Loader2 className="spinning-icon" size={48} />
                <p>Loading Payslip Details...</p>
                <style>{`
                    .loading-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; color: var(--text-secondary); gap: 1rem; }
                    .spinning-icon { animation: spin 1s linear infinite; color: #B800C4; }
                    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                `}</style>
            </div>
        );
    }

    return (
        <div className="payslip-detail-page">
            <button className="back-nav-btn" onClick={() => navigate('/payslips')}>
                <div className="back-icon-box">
                    <ChevronLeft size={20} />
                </div>
                <span>Back</span>
            </button>

            <div className="payslip-main-card fade-in">
                <div className="card-header">
                    <div className="header-info">
                        <h1 className="card-title">Your Payslips</h1>
                        <div className="user-meta">
                            <span className="user-name-label">{user?.name || 'Paul Barber'}</span>
                            <span className="separator">|</span>
                            <span className="id-label">ID: {user?.consultantId || 'HRM65'}</span>
                        </div>
                    </div>

                    <div className="header-actions">
                        <div className="month-picker">
                            <select
                                value={selectedMonth}
                                onChange={(e) => setSelectedMonth(e.target.value)}
                                className="styled-select"
                            >
                                {months.map(m => <option key={m} value={m}>{m}</option>)}
                            </select>
                            <ChevronDown size={16} className="select-arrow" />
                        </div>
                        <button className="icon-action-btn" onClick={() => setShowSalary(!showSalary)}>
                            {showSalary ? <EyeOff size={20} color="#B800C4" /> : <Eye size={20} color="#B800C4" />}
                        </button>
                        <button className="icon-action-btn" title="Download" onClick={handleDownload}>
                            <Download size={20} color="#B800C4" />
                        </button>
                    </div>
                </div>

                <div className="chart-content-grid">
                    <div className="viz-container">
                        <div className="donut-wrapper">
                            <svg viewBox="0 0 100 100" className="donut-svg">
                                <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border-color)" strokeWidth="10" />
                                <circle
                                    cx="50" cy="50" r="45"
                                    fill="none"
                                    stroke="url(#blueGradient)"
                                    strokeWidth="10"
                                    strokeDasharray="210 283"
                                    strokeLinecap="round"
                                    transform="rotate(-90 50 50)"
                                />
                                <circle
                                    cx="50" cy="50" r="45"
                                    fill="none"
                                    stroke="#A855F7"
                                    strokeWidth="10"
                                    strokeDasharray="40 283"
                                    strokeDashoffset="-210"
                                    strokeLinecap="round"
                                    transform="rotate(-90 50 50)"
                                />
                                <defs>
                                    <linearGradient id="blueGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor="#3B82F6" />
                                        <stop offset="100%" stopColor="#60A5FA" />
                                    </linearGradient>
                                </defs>
                            </svg>
                            <div className="donut-center">
                                <span className="inner-label">Net Salary</span>
                                <span className="inner-value">{showSalary ? formatCurrency(payslip?.take_home || 0) : '********'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="metrics-container">
                        <div className="metrics-grid">
                            <div className="metric-item">
                                <div className="indicator bar-blue"></div>
                                <div className="metric-details">
                                    <span className="m-label">Basic Salary</span>
                                    <span className="m-value">{showSalary ? formatCurrency((payslip?.gross_pay || 0) * 0.6) : '*****'}</span>
                                </div>
                            </div>
                            <div className="metric-item">
                                <div className="indicator bar-purple"></div>
                                <div className="metric-details">
                                    <span className="m-label">HRA</span>
                                    <span className="m-value">{showSalary ? formatCurrency((payslip?.gross_pay || 0) * 0.2) : '*****'}</span>
                                </div>
                            </div>
                            <div className="metric-item">
                                <div className="indicator bar-teal"></div>
                                <div className="metric-details">
                                    <span className="m-label">Other Allowance</span>
                                    <span className="m-value">{showSalary ? formatCurrency(payslip?.reimbursement || 0) : '*****'}</span>
                                </div>
                            </div>
                            <div className="metric-item">
                                <div className="indicator bar-orange"></div>
                                <div className="metric-details">
                                    <span className="m-label">Deductions</span>
                                    <span className="m-value">{showSalary ? formatCurrency(payslip?.deductions || 0) : '*****'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                .payslip-detail-page { padding: 1rem 0; }
                .back-nav-btn { display: flex; align-items: center; gap: 0.75rem; background: none; border: none; cursor: pointer; margin-bottom: 2rem; color: var(--text-primary); font-weight: 700; font-size: 0.95rem; }
                .back-icon-box { width: 32px; height: 32px; background: var(--card-bg); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px var(--shadow-color); border: 1px solid var(--border-color); }
                .payslip-main-card { background: var(--card-bg); border-radius: 32px; padding: 3rem; box-shadow: 0 10px 40px var(--shadow-color); max-width: 800px; border: 1px solid var(--border-color); transition: background-color 0.3s ease; }
                .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 3.5rem; }
                .card-title { font-size: 1.8rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.25rem; }
                .user-meta { display: flex; align-items: center; gap: 0.75rem; color: var(--text-secondary); font-weight: 600; font-size: 0.9rem; }
                .header-actions { display: flex; align-items: center; gap: 1.25rem; }
                .month-picker { position: relative; background: var(--bg-color); border-radius: 12px; padding: 0.5rem 1rem; display: flex; align-items: center; border: 1px solid var(--border-color); }
                .styled-select { appearance: none; background: transparent; border: none; outline: none; font-weight: 700; color: var(--text-primary); padding-right: 1.5rem; cursor: pointer; }
                .select-arrow { position: absolute; right: 0.75rem; pointer-events: none; color: var(--text-secondary); }
                .icon-action-btn { width: 44px; height: 44px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 4px var(--shadow-color); }
                .icon-action-btn:hover { box-shadow: 0 4px 12px rgba(184, 0, 196, 0.2); transform: translateY(-2px); border-color: #B800C4; }
                .chart-content-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 4rem; align-items: center; }
                .donut-wrapper { position: relative; width: 260px; height: 260px; margin: 0 auto; }
                .donut-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; display: flex; flex-direction: column; }
                .inner-label { color: #a78bfa; font-size: 0.85rem; font-weight: 700; }
                .inner-value { color: var(--text-primary); font-size: 1.5rem; font-weight: 800; letter-spacing: 0.5px; }
                .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2.5rem 1.5rem; }
                .metric-item { display: flex; gap: 1rem; }
                .indicator { width: 4px; height: 40px; border-radius: 10px; }
                .bar-blue { background: #3B82F6; }
                .bar-purple { background: #A855F7; }
                .bar-teal { background: #2DD4BF; }
                .bar-orange { background: #F97316; }
                .metric-details { display: flex; flex-direction: column; gap: 0.25rem; }
                .m-label { color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; }
                .m-value { color: var(--text-primary); font-size: 1rem; font-weight: 800; letter-spacing: 0.5px; }
                .fade-in { animation: fadeIn 0.4s ease-out; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                @media (max-width: 900px) {
                    .chart-content-grid { grid-template-columns: 1fr; gap: 3rem; }
                    .payslip-main-card { padding: 2rem; }
                    .card-header { flex-direction: column; gap: 1.5rem; }
                }
            `}</style>
        </div>
    );
};

export default PayslipDetail;
