// File: apps/pkm-app/pages/staging.js
import { useState, useEffect } from 'react';
import axios from 'axios';
import StagingTable from '../components/StagingTable';
import Link from 'next/link';

export default function Staging() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchFiles();
  }, [refreshKey]);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await axios.get('https://pkm-indexer-production.up.railway.app/staging');
      console.log("Staging response:", response.data);
      setFiles(response.data.files || []);
      setError('');
    } catch (err) {
      console.error("Failed to load staging files:", err);
      setError('Failed to load staging files. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (file) => {
    try {
      setLoading(true);
      console.log("Approving file:", file);
      await axios.post('https://pkm-indexer-production.up.railway.app/approve', { file });
      // Force a refresh of the file list
      setRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error("Approval error:", err);
      setError('Failed to approve file. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ color: '#333' }}>Review Staging Files</h1>
        <div>
          <Link href="/" style={{ 
            marginRight: '15px',
            padding: '8px 15px', 
            backgroundColor: '#f0f0f0', 
            color: '#333',
            textDecoration: 'none',
            borderRadius: '4px'
          }}>
            ← Back to Home
          </Link>
          <button 
            onClick={() => setRefreshKey(prev => prev + 1)}
            style={{ 
              padding: '8px 15px', 
              backgroundColor: '#4CAF50', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Refresh
          </button>
        </div>
      </div>
      
      {error && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#ffebee', 
          color: '#c62828', 
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          {error}
        </div>
      )}
      
      {loading ? (
        <div style={{ 
          padding: '20px', 
          textAlign: 'center', 
          color: '#666',
          backgroundColor: '#f5f5f5',
          borderRadius: '4px'
        }}>
          Loading staging files...
        </div>
      ) : (
        <StagingTable files={files} onApprove={handleApprove} />
      )}
      
      <div style={{ marginTop: '30px', fontSize: '14px', color: '#666', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
        <h3 style={{ margin: '0 0 10px 0' }}>About the Staging Process</h3>
        <p>
          Files appear here after being processed but before being added to your knowledge base.
          This gives you a chance to review and modify the AI-generated metadata before approval.
        </p>
        <p>
          <strong>New files will appear after:</strong>
        </p>
        <ol>
          <li>Adding files to your Google Drive PKM/Inbox folder</li>
          <li>Clicking "Sync Google Drive" on the home page</li>
          <li>The system processes the files (this may take a moment)</li>
        </ol>
      </div>
    </div>
  );
}