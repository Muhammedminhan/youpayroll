import React, { useState, useEffect } from 'react';
import { Search, Plus, Book, ChevronRight, Clock, User, Tag, Edit3, Save, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../api';

const hrGuideContent = `
# YOUPayroll HR Guide

The YOUPayroll project is designed to provide users and employees with easy access to their payroll information.

### What You Can Do
View and manage your payroll details with ease.

### What to Look For
Ensure your profile and salary details are accurate and up to date.

### What You Need to Know
Familiarize yourself with key features, access permissions, and payroll timelines.

### How to Access
Log in using your credentials via the designated portal to securely access your payroll.

---

## User Management

### Adding a User
1. Go to **Authentication and Authorization**.
2. Click **Add** next to Users.
3. Enter a **Username** in the format: \`user@yougotagift\`.
4. Enter a **Password** (recommended: generate using 1Password).
5. Click **Save**.

Once created, you will be redirected to the **User Details** page.
- Add **Personal Information**.
- Tick the **Staff Status** checkbox.
- *Do not* tick the **Superuser Status** checkbox unless specifically required.
- Assign the User to a **Group** (e.g., HR).
- Click the arrow button to move the user into that group.
- Click **Save**.

---

## Component Management
Components manage additional earnings or deductions.

### Adding a Component
1. Go to **Component Management**.
2. Click **Add Component**.
3. Enter the **Component Name**.
4. Add the **Operations** that define how it's applied.
5. Click **Save**.

---

## Payee Management
Manage employee records and TDS setup.

- **HRM ID**: Enter from Zoho People.
- **TDS Type**: Select legal name and percentage.
- **Status**: Active, Removed, or Disengaged.
- **Is Deleted**: Tick this instead of deleting if the employee no longer exists.

### Bank Details
1. Select Payee.
2. Enter Bank Details & Save.
3. **Acknowledge**: Payee must log in to acknowledge.
4. **Correction**: If payee adds comments, update details and ask for re-acknowledgement.

---

## Pay Run Management
A Pay Run groups employee payments for a selected month.

### Running a Pay Run
1. Select **Month & Year**.
2. Created Pay Run starts as **DUE**.
3. Run the latest Pay Run (DUE -> COMPLETED).
4. **Check Error Log**: Review logs for successful registration or errors.
5. **Handling Errors**: If errors exist, **Reject Pay Run**, fix issues, and create a new one.

---

## Payslip Management (Pay Record Register)
Once COMPLETED, system generates payslips.

1. Go to **Pay Record Register**.
2. Select employees whose Pay Run is completed.
3. Review and **Edit Components** if needed (Earnings/Deductions).
4. Mark as **Approved**. *Note: No further edits can be added after Approval.*
`;

const Wiki = () => {
  const [pages, setPages] = useState([]);
  const [categories, setCategories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPage, setSelectedPage] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editData, setEditData] = useState({ title: '', content: '', category: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    // Set HR Guide as default view
    setSelectedPage({
      id: 'hr-guide',
      title: 'YOUPayroll HR Guide',
      content: hrGuideContent,
      updated_at: new Date().toISOString(),
      category_name: 'Manual'
    });
  }, []);

  const fetchData = async () => {
    try {
      const [pagesRes, catsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/wiki-pages/`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/wiki-categories/`, { credentials: 'include' })
      ]);

      if (pagesRes.ok && catsRes.ok) {
        const pagesData = await pagesRes.json();
        const catsData = await catsRes.json();
        setPages(Array.isArray(pagesData) ? pagesData : []);
        setCategories(Array.isArray(catsData) ? catsData : []);
      }
    } catch (error) {
      console.error('Error fetching wiki data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editData.title || !editData.title.trim()) {
      alert('Please enter a page title.');
      return;
    }

    setIsSaving(true);

    try {
      const isExisting = selectedPage && selectedPage.id && !String(selectedPage.id).includes('local');

      const url = isExisting
        ? `${API_BASE_URL}/wiki-pages/${selectedPage.slug}/`
        : `${API_BASE_URL}/wiki-pages/`;

      const method = isExisting ? 'PATCH' : 'POST';

      const payload = {
        title: editData.title,
        content: editData.content,
        category: editData.category || null
      };

      const csrfToken = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ?? '';
      const response = await fetch(url, {
        method,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const savedData = await response.json();
        setPages(prev => {
          const index = prev.findIndex(p => String(p.id) === String(savedData.id));
          if (index !== -1) {
            const newPages = [...prev];
            newPages[index] = savedData;
            return newPages;
          }
          return [savedData, ...prev];
        });
        setSelectedPage(savedData);
        setIsEditing(false);
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
    } catch (err) {
      console.error('Save error:', err);
      alert(`Failed to save documentation: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setIsSaving(false);
  };

  const filteredPages = pages.filter(page =>
    (page.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (page.content || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="wiki-loading">
      <div className="spinner"></div>
      <p>Loading YOUPayroll Wiki...</p>
    </div>
  );

  return (
    <div className="wiki-container">
      <div className="wiki-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-top">
            <h3 className="sidebar-label">Wiki Index</h3>
            <button className="icon-btn-refresh" onClick={fetchData} title="Sync with server">
              <Clock size={16} />
            </button>
          </div>

          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search wiki..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>
                <X size={14} />
              </button>
            )}
          </div>

          <button className="create-page-btn" onClick={() => {
            setSelectedPage(null);
            setEditData({ title: '', content: '', category: categories[0]?.id || '' });
            setIsEditing(true);
          }}>
            <Plus size={18} />
            Create New Page
          </button>
        </div>

        <div className="sidebar-nav">
          {!searchQuery && (
            <div className="nav-group">
              <h3>CATEGORIES</h3>
              <div className="nav-list">
                {categories.map(cat => (
                  <div key={cat.id} className="nav-item category">
                    <Tag size={16} />
                    <span>{cat.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="nav-group">
            <h3>SYSTEM GUIDES</h3>
            <div className="nav-list">
              <div
                className={`nav-item page ${selectedPage?.id === 'hr-guide' ? 'active' : ''}`}
                onClick={() => {
                  setSelectedPage({
                    id: 'hr-guide',
                    title: 'YOUPayroll HR Guide',
                    content: hrGuideContent,
                    updated_at: new Date().toISOString(),
                    category_name: 'Manual'
                  });
                  setIsEditing(false);
                }}
              >
                <Book size={16} />
                <span>HR User Guide</span>
                <ChevronRight size={14} className="chevron" />
              </div>
            </div>
          </div>

          <div className="nav-group">
            <h3>{searchQuery ? `SEARCH RESULTS (${filteredPages.length})` : 'PAGES'}</h3>
            <div className="nav-list">
              {filteredPages.length > 0 ? (
                filteredPages.map(page => (
                  <div
                    key={page.id}
                    className={`nav-item page ${selectedPage?.id === page.id ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedPage(page);
                      setIsEditing(false);
                    }}
                  >
                    <Book size={16} />
                    <span className="truncate">{page.title}</span>
                    <ChevronRight size={14} className="chevron" />
                  </div>
                ))
              ) : (
                <div className="no-results">
                  <p>No results found for "{searchQuery}"</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="wiki-content">
        {isEditing ? (
          <div className="editor-layout">
            <div className="editor-header">
              <input
                className="edit-title-input"
                value={editData.title}
                onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                placeholder="Enter Page Title..."
                autoFocus
              />
              <select
                className="edit-category-select"
                value={editData.category}
                onChange={(e) => setEditData({ ...editData, category: e.target.value })}
              >
                <option value="">Select Category</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
            </div>

            <textarea
              className="edit-content-textarea"
              value={editData.content}
              onChange={(e) => setEditData({ ...editData, content: e.target.value })}
              placeholder="Write your documentation here (Markdown supported)..."
            />

            <div className="editor-footer">
              <button className="btn-cancel" onClick={handleCancel} disabled={isSaving}>
                <X size={18} />
                Cancel
              </button>
              <button className="btn-save" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving..." : <><Save size={18} /> Save Documentation</>}
              </button>
            </div>
          </div>
        ) : selectedPage ? (
          <div className="viewer-layout">
            <div className="page-header">
              <div className="header-main">
                <h1>{selectedPage.title}</h1>
                <button className="btn-edit" onClick={() => {
                  setEditData({ title: selectedPage.title, content: selectedPage.content, category: selectedPage.category });
                  setIsEditing(true);
                }}>
                  <Edit3 size={18} />
                  Edit Page
                </button>
              </div>
              <div className="page-metadata">
                <span className="meta-tag"><User size={14} /> {selectedPage.author_name || 'Team member'}</span>
                <span className="meta-tag"><Clock size={14} /> {new Date(selectedPage.updated_at).toLocaleDateString()}</span>
                {selectedPage.category_name && (
                  <span className="meta-tag"><Tag size={14} /> {selectedPage.category_name}</span>
                )}
              </div>
            </div>
            <div className="content-rendered">
              <ReactMarkdown>{selectedPage.content}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="wiki-empty">
            <div className="empty-icon-wrapper">
              <Book size={80} />
            </div>
            <h2>Technical Wiki</h2>
            <p>Select a topic from the sidebar or start a new documentation entry.</p>
            <button className="btn-create-first" onClick={() => {
              setSelectedPage(null);
              setEditData({ title: '', content: '', category: categories[0]?.id || '' });
              setIsEditing(true);
            }}>
              <Plus size={20} />
              New Documentation
            </button>
          </div>
        )}
      </div>

      <style>{`
        .wiki-container { display: flex; height: calc(100vh - 8rem); background: var(--card-bg); border-radius: 24px; overflow: hidden; box-shadow: 0 10px 40px var(--shadow-color); border: 1px solid var(--border-color); transition: background-color 0.3s ease; }
        .wiki-sidebar { width: 320px; background: var(--bg-color); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; }
        .sidebar-header { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; border-bottom: 1px solid var(--border-color); }
        .sidebar-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }
        .sidebar-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.1em; margin: 0; }
        .icon-btn-refresh { background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 4px; border-radius: 4px; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
        .icon-btn-refresh:hover { color: #B800C4; background: rgba(184, 0, 196, 0.05); }
        .search-box { display: flex; align-items: center; gap: 0.5rem; background: var(--card-bg); padding: 0.6rem 0.8rem; border-radius: 10px; border: 1px solid var(--border-color); transition: border-color 0.2s; }
        .search-box:focus-within { border-color: #B800C4; }
        .search-icon { color: var(--text-secondary); }
        .search-box input { border: none; outline: none; width: 100%; font-size: 0.85rem; color: var(--text-primary); background: transparent; }
        .clear-search { background: var(--bg-color); border: none; color: var(--text-secondary); width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
        .create-page-btn { display: flex; align-items: center; justify-content: center; gap: 0.5rem; background: #B800C4; color: white; border: none; padding: 0.8rem; border-radius: 12px; font-weight: 700; cursor: pointer; font-size: 0.9rem; }
        .sidebar-nav { flex: 1; overflow-y: auto; padding: 1.5rem; }
        .nav-group { margin-bottom: 2rem; }
        .nav-group h3 { font-size: 0.7rem; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.1em; margin-bottom: 0.75rem; }
        .nav-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.7rem 0.8rem; border-radius: 10px; cursor: pointer; color: var(--text-secondary); font-size: 0.9rem; transition: all 0.2s; }
        .nav-item:hover { background: rgba(184, 0, 196, 0.05); color: #B800C4; }
        .nav-item.active { background: var(--card-bg); color: #B800C4; font-weight: 600; box-shadow: 0 2px 8px var(--shadow-color); border: 1px solid var(--border-color); }
        .wiki-content { flex: 1; overflow-y: auto; background: var(--card-bg); position: relative; }
        .editor-layout { display: flex; flex-direction: column; height: 100%; padding: 2.5rem; gap: 1.5rem; }
        .editor-header { display: flex; flex-direction: column; gap: 1rem; }
        .edit-title-input { font-size: 2.2rem; font-weight: 800; border: none; border-bottom: 2px solid var(--border-color); outline: none; padding-bottom: 0.5rem; color: var(--text-primary); background: transparent; }
        .edit-category-select { width: fit-content; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-color); color: var(--text-primary); }
        .edit-content-textarea { flex: 1; border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; font-family: inherit; font-size: 1.05rem; line-height: 1.6; resize: none; outline: none; background: var(--bg-color); color: var(--text-primary); }
        .editor-footer { display: flex; justify-content: flex-end; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); background: var(--card-bg); }
        .btn-cancel, .btn-save { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.5rem; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; }
        .btn-cancel { background: var(--bg-color); color: var(--text-secondary); }
        .btn-save { background: #B800C4; color: white; box-shadow: 0 4px 12px rgba(184, 0, 196, 0.2); }
        .viewer-layout { padding: 3rem 4rem; max-width: 900px; margin: 0 auto; color: var(--text-primary); }
        .header-main { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
        .header-main h1 { font-size: 2.8rem; font-weight: 800; color: var(--text-primary); margin: 0; }
        .btn-edit { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-secondary); font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-edit:hover { border-color: #B800C4; color: #B800C4; }
        .page-metadata { display: flex; gap: 1.5rem; margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border-color); }
        .meta-tag { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: var(--text-secondary); }
        .content-rendered { font-size: 1.1rem; line-height: 1.7; color: var(--text-primary); }
        .wiki-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }
        .empty-icon-wrapper { width: 120px; height: 120px; background: var(--bg-color); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); margin-bottom: 1.5rem; }
        .btn-create-first { background: #B800C4; color: white; border: none; padding: 1rem 1.5rem; border-radius: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; }
        .spinner { width: 40px; height: 40px; border: 4px solid var(--bg-color); border-top: 4px solid #B800C4; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .wiki-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 1rem; color: var(--text-secondary); }
        .truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
        @media (max-width: 768px) {
          .wiki-container { flex-direction: column; height: auto; border-radius: 0; border: none; box-shadow: none; margin-bottom: 2rem; }
          .wiki-sidebar { width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--border-color); }
          .sidebar-nav { padding: 1rem; max-height: 300px; }
          .wiki-content { height: auto; min-height: 50vh; }
          .viewer-layout { padding: 1.5rem; }
          .header-main h1 { font-size: 1.75rem; }
          .editor-layout { padding: 1.25rem; }
          .edit-title-input { font-size: 1.5rem; }
        }
      `}</style>
    </div>
  );
};

export default Wiki;
