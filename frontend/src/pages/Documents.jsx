import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Download, Loader2, FileText } from 'lucide-react';
import { API_BASE_URL, MEDIA_BASE_URL } from '../api';

const Documents = () => {
   const navigate = useNavigate();
   const [documents, setDocuments] = useState([]);
   const [loading, setLoading] = useState(false);

   // Fetch documents from API
   useEffect(() => {
      fetchDocuments();
   }, []);

   const fetchDocuments = async () => {
      setLoading(true);
      try {
         const response = await fetch(`${API_BASE_URL}/documents/`, {
            credentials: 'include',
         });

         if (response.ok) {
            const data = await response.json();
            setDocuments(data);
         } else {
            throw new Error('Failed to fetch');
         }
      } catch (error) {
         console.error('Error fetching documents:', error);
      } finally {
         setLoading(false);
      }
   };

   const handleDownload = async (doc) => {
      if (!doc.file) {
         alert('File not available for this record.');
         return;
      }

      const baseUrl = MEDIA_BASE_URL;
      const fullUrl = doc.file.startsWith('http') ? doc.file : `${baseUrl}${doc.file}`;

      try {
         const response = await fetch(fullUrl, { credentials: 'include' });

         if (!response.ok) throw new Error('Download failed');

         const blob = await response.blob();
         const url = window.URL.createObjectURL(blob);
         const link = document.createElement('a');
         link.href = url;
         link.setAttribute('download', `${doc.title.replace(/\s+/g, '_')}.pdf`);
         document.body.appendChild(link);
         link.click();
         link.remove();
         window.URL.revokeObjectURL(url);
      } catch (error) {
         console.error('Error downloading document:', error);
         window.open(fullUrl, '_blank');
      }
   };

   return (
      <div className="documents-page-v2">
         <header className="page-header">
            <button className="back-nav-btn" onClick={() => navigate('/')}>
               <div className="back-icon-box">
                  <ChevronLeft size={20} />
               </div>
               <span>Back</span>
            </button>
         </header>

         <div className="documents-card fade-in">
            <h1 className="card-title">Form 16</h1>

            <div className="table-container desktop-only-table">
               <table className="docs-table">
                  <thead>
                     <tr>
                        <th>Financial Year</th>
                        <th>File Type</th>
                        <th>Uploaded On</th>
                        <th className="action-col">Action</th>
                     </tr>
                  </thead>
                  <tbody>
                     {loading ? (
                        <tr>
                           <td colSpan="4" className="status-cell">
                              <Loader2 className="spinning" size={24} />
                              <span>Loading documents...</span>
                           </td>
                        </tr>
                     ) : documents.length > 0 ? (
                        documents.map((doc) => (
                           <tr key={doc.id}>
                              <td className="year-cell">
                                                                  {(() => {
                                    const date = new Date(doc.updated_at);
                                    const year = date.getFullYear();
                                    const month = date.getMonth();
                                    const fyStart = month < 3 ? year - 1 : year;
                                    return `${fyStart}-${fyStart + 1}`;
                                 })()}
                              </td>
                              <td className="type-cell">{doc.title}</td>
                              <td className="date-cell">
                                 {new Date(doc.updated_at).toLocaleDateString('en-GB', {
                                    day: '2-digit',
                                    month: 'long',
                                    year: 'numeric'
                                 })}
                              </td>
                              <td className="action-col">
                                 <button
                                    className="download-action-btn"
                                    onClick={() => handleDownload(doc)}
                                    title={`Download ${doc.title}`}
                                 >
                                    <Download size={18} />
                                 </button>
                              </td>
                           </tr>
                        ))
                     ) : (
                        <tr>
                           <td colSpan="4" className="status-cell">No documents found.</td>
                        </tr>
                     )}
                  </tbody>
               </table>
            </div>

            <div className="mobile-docs-view">
               {loading ? (
                  <div className="loading-state">
                     <Loader2 className="spinning" size={32} />
                     <p>Loading documents...</p>
                  </div>
               ) : documents.length > 0 ? (
                  <div className="docs-list-mobile">
                     {documents.map(doc => (
                        <div key={doc.id} className="doc-mobile-card">
                           <div className="doc-icon-v2">
                              <FileText size={24} color="#B800C4" />
                           </div>
                           <div className="doc-details-v2">
                              <h4>{doc.title}</h4>
                              <span className="doc-year-v2">Financial Year {(() => {
                                 const date = new Date(doc.updated_at);
                                 const year = date.getFullYear();
                                 const month = date.getMonth();
                                 const fyStart = month < 3 ? year - 1 : year;
                                 return `${fyStart}-${fyStart + 1}`;
                              })()}</span>
                              <span className="doc-date-v2">Uploaded on {new Date(doc.updated_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
                           </div>
                           <button className="doc-download-btn-v2" onClick={() => handleDownload(doc)}>
                              <Download size={20} />
                           </button>
                        </div>
                     ))}
                  </div>
               ) : (
                  <div className="empty-state">No documents found.</div>
               )}
            </div>
         </div>

         <style>{`
            .documents-page-v2 {
               padding: 1rem 0;
               padding-bottom: 5rem;
            }

            .desktop-only-table { display: block; }
            .mobile-docs-view { display: none; }

            @media (max-width: 768px) {
                .desktop-only-table { display: none; }
                .mobile-docs-view { display: block; }
                .documents-card { padding: 1.25rem; border-radius: 20px; }
                .card-title { font-size: 1.25rem; margin-bottom: 1.25rem; font-weight: 800; }
            }

            .docs-list-mobile { display: flex; flex-direction: column; gap: 0.85rem; }
            .doc-mobile-card { background: var(--bg-color); padding: 1rem; border-radius: 18px; display: flex; align-items: center; gap: 0.85rem; border: 1px solid var(--border-color); }
            .doc-icon-v2 { width: 40px; height: 40px; border-radius: 10px; background: var(--card-bg); display: flex; align-items: center; justify-content: center; }
            .doc-details-v2 { flex: 1; display: flex; flex-direction: column; gap: 1px; }
            .doc-details-v2 h4 { font-size: 0.9rem; font-weight: 800; color: var(--text-primary); margin: 0; }
            .doc-year-v2 { font-size: 0.73rem; color: var(--text-secondary); font-weight: 600; }
            .doc-date-v2 { font-size: 0.65rem; color: var(--text-secondary); opacity: 0.75; }
            
            .doc-download-btn-v2 { width: 36px; height: 36px; border-radius: 50%; background: #B800C4; color: white; border: none; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(184, 0, 196, 0.15); }

            .page-header {
               margin-bottom: 2rem;
            }

            .back-nav-btn {
               display: flex;
               align-items: center;
               gap: 0.75rem;
               background: none;
               border: none;
               cursor: pointer;
               color: var(--text-primary);
               font-weight: 700;
               font-size: 0.95rem;
               transition: all 0.2s;
            }

            .back-icon-box {
               width: 32px;
               height: 32px;
               background: var(--card-bg);
               border-radius: 50%;
               display: flex;
               align-items: center;
               justify-content: center;
               box-shadow: 0 4px 10px var(--shadow-color);
               border: 1px solid var(--border-color);
            }

            .back-nav-btn:hover {
               transform: translateX(-4px);
               color: #B800C4;
            }

            .documents-card {
               background: var(--card-bg);
               border-radius: 32px;
               padding: 2.5rem;
               box-shadow: 0 10px 40px var(--shadow-color);
               max-width: 900px;
               border: 1px solid var(--border-color);
               transition: background-color 0.3s ease;
            }

            .card-title {
               font-size: 1.75rem;
               font-weight: 800;
               color: var(--text-primary);
               margin-bottom: 2rem;
            }

            .table-container {
                overflow-x: auto;
            }

            .docs-table {
               width: 100%;
               border-collapse: collapse;
            }

            .docs-table th {
               text-align: left;
               background: var(--bg-color);
               padding: 1.25rem 1.5rem;
               font-size: 0.85rem;
               font-weight: 700;
               color: var(--text-secondary);
               text-transform: capitalize;
            }

            .docs-table th:first-child { border-top-left-radius: 16px; border-bottom-left-radius: 16px; }
            .docs-table th:last-child { border-top-right-radius: 16px; border-bottom-right-radius: 16px; }

            .docs-table td {
               padding: 1.5rem;
               border-bottom: 1px solid var(--border-color);
               font-size: 0.95rem;
               color: var(--text-primary);
               font-weight: 600;
            }

            .docs-table tr:last-child td {
               border-bottom: none;
            }

            .year-cell { color: var(--text-secondary) !important; }
            .action-col { text-align: right; width: 100px; }

            .download-action-btn {
               width: 36px;
               height: 36px;
               border-radius: 50%;
               border: 1px solid var(--border-color);
               background: var(--card-bg);
               display: flex;
               align-items: center;
               justify-content: center;
               color: #B800C4;
               cursor: pointer;
               transition: all 0.22s;
            }

            .download-action-btn:hover {
               background: #B800C4;
               color: white;
               transform: scale(1.1);
               box-shadow: 0 4px 12px rgba(184, 0, 196, 0.2);
            }

            .status-cell {
               text-align: center;
               padding: 4rem !important;
               color: var(--text-secondary);
            }

            .loading-state { padding: 4rem 0; text-align: center; color: var(--text-secondary); }

            .spinning {
               animation: spin 1s linear infinite;
               color: #B800C4;
            }

            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .fade-in { animation: fadeIn 0.4s ease-out; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
         `}</style>
      </div>
   );
};

export default Documents;
