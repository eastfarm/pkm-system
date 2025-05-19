// File: apps/pkm-app/pages/index.js
import { useState, useEffect } from 'react';
import axios from 'axios';
import Link from 'next/link';

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState('');
  const [file, setFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [organizeStatus, setOrganizeStatus] = useState('');
  const [isOrganizing, setIsOrganizing] = useState(false);
  const [syncStatus, setSyncStatus] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [fileStats, setFileStats] = useState(null);

  // Fetch file stats when the component loads
  useEffect(() => {
    fetchFileStats();
  }, []);

  const fetchFileStats = async () => {
    try {
      const response = await axios.get('https://pkm-indexer-production.up.railway.app/file-stats');
      setFileStats(response.data);
    } catch (error) {
      console.error('Failed to fetch file stats:', error);
    }
  };

  const handleQuery = async () => {
    try {
      const response = await axios.post('https://pkm-indexer-production.up.railway.app/search', { query });
      setResults(response.data.response);
    } catch (error) {
      setResults('Error: Could not fetch results');
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      setUploadMessage('Please select a file');
      return;
    }

    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target.result;
      try {
        const response = await axios.post('https://pkm-indexer-production.up.railway.app/upload/Inbox', {
          filename: file.name,
          content: content.split(',')[1], // Base64 content (removing "data:..." prefix)
        });
        setUploadMessage(response.data.status);
        // Refresh file stats after upload
        fetchFileStats();
      } catch (error) {
        setUploadMessage('Upload failed: ' + error.message);
      }
    };
    reader.readAsDataURL(file);
  };

  const triggerOrganize = async () => {
    setIsOrganizing(true);
    setOrganizeStatus('Processing files...');
    try {
      const response = await axios.post('https://pkm-indexer-production.up.railway.app/trigger-organize');
      setOrganizeStatus(`✅ ${response.data.status}`);
      // Refresh file stats after organizing
      fetchFileStats();
    } catch (error) {
      setOrganizeStatus(`❌ Failed: ${error.message}`);
    } finally {
      setIsOrganizing(false);
    }
  };

  const triggerDriveSync = async () => {
    setIsSyncing(true);
    setSyncStatus('Syncing with Google Drive...');
    try {
      const response = await axios.post('https://pkm-indexer-production.up.railway.app/sync-drive');
      
      // Handle response with debug info
      if (response.data.debug) {
        console.log("Sync debug info:", response.data.debug);
        
        // Check for specific issues
        if (response.data.debug.error) {
          setSyncStatus(`❌ ${response.data.status}: ${response.data.debug.error}`);
        } else if (response.data.debug.inbox_files_count === 0) {
          setSyncStatus(`ℹ️ ${response.data.status}`);
        } else {
          setSyncStatus(`✅ ${response.data.status}`);
        }
      } else {
        setSyncStatus(`✅ ${response.data.status}`);
      }
      
      // Refresh file stats after sync
      fetchFileStats();
    } catch (error) {
      console.error("Sync error:", error);
      if (error.response && error.response.data) {
        setSyncStatus(`❌ Failed: ${error.response.data.status || error.message}`);
      } else {
        setSyncStatus(`❌ Failed: ${error.message}`);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#333', borderBottom: '2px solid #eee', paddingBottom: '10px' }}>Personal Knowledge Management</h1>
      
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div style={{ flex: '1' }}>
          <h2>System Controls</h2>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
            <button 
              onClick={triggerOrganize} 
              disabled={isOrganizing}
              style={{ 
                padding: '10px 15px', 
                backgroundColor: isOrganizing ? '#ccc' : '#4CAF50', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: isOrganizing ? 'not-allowed' : 'pointer'
              }}
            >
              {isOrganizing ? 'Processing...' : 'Process Files'}
            </button>
            <button 
              onClick={triggerDriveSync} 
              disabled={isSyncing}
              style={{ 
                padding: '10px 15px', 
                backgroundColor: isSyncing ? '#ccc' : '#2196F3', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: isSyncing ? 'not-allowed' : 'pointer'
              }}
            >
              {isSyncing ? 'Syncing...' : 'Sync Google Drive'}
            </button>
          </div>
          {organizeStatus && <div style={{ marginBottom: '10px' }}>{organizeStatus}</div>}
          {syncStatus && <div style={{ marginBottom: '10px' }}>{syncStatus}</div>}
        </div>

        <div style={{ flex: '1' }}>
          <h2>Navigation</h2>
          <ul style={{ listStyleType: 'none', padding: '0' }}>
            <li style={{ margin: '10px 0' }}>
              <Link href="/staging" style={{ 
                display: 'block',
                padding: '10px', 
                backgroundColor: '#f0f0f0', 
                borderRadius: '4px',
                color: '#333',
                textDecoration: 'none'
              }}>
                🔍 Review Staging Files
              </Link>
            </li>
            <li style={{ margin: '10px 0' }}>
              <a href="https://pkm-indexer-production.up.railway.app/logs" target="_blank" rel="noopener noreferrer" style={{ 
                display: 'block',
                padding: '10px', 
                backgroundColor: '#f0f0f0', 
                borderRadius: '4px',
                color: '#333',
                textDecoration: 'none'
              }}>
                📋 View Processing Logs
              </a>
            </li>
          </ul>
        </div>
      </div>

      {fileStats && (
        <div style={{ 
          backgroundColor: '#f9f9f9', 
          padding: '15px', 
          borderRadius: '5px',
          marginBottom: '20px',
          border: '1px solid #ddd'
        }}>
          <h2 style={{ marginTop: '0' }}>System Stats</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <h3 style={{ fontSize: '16px', margin: '0 0 5px 0' }}>Inbox</h3>
              <p style={{ margin: '0' }}>{fileStats.inbox_count || 0} files waiting</p>
            </div>
            <div>
              <h3 style={{ fontSize: '16px', margin: '0 0 5px 0' }}>Processed</h3>
              <p style={{ margin: '0' }}>{fileStats.metadata_count || 0} metadata files</p>
            </div>
            <div>
              <h3 style={{ fontSize: '16px', margin: '0 0 5px 0' }}>Sources</h3>
              <p style={{ margin: '0' }}>
                {fileStats.source_types ? Object.entries(fileStats.source_types).map(([type, count]) => (
                  `${type}: ${count}`
                )).join(', ') : 'None'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: '1', minWidth: '300px' }}>
          <h2>Query Knowledge Base</h2>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask your KB..."
            style={{ 
              width: '100%', 
              padding: '10px', 
              marginBottom: '10px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
          <button 
            onClick={handleQuery} 
            style={{ 
              padding: '10px 20px',
              backgroundColor: '#673AB7',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Search
          </button>
          <div style={{ 
            marginTop: '20px', 
            whiteSpace: 'pre-wrap',
            backgroundColor: results ? '#f9f9f9' : 'transparent',
            padding: results ? '15px' : '0',
            borderRadius: '4px',
            border: results ? '1px solid #ddd' : 'none'
          }}>
            {results}
          </div>
        </div>

        <div style={{ flex: '1', minWidth: '300px' }}>
          <h2>Upload File to Inbox</h2>
          <input
            type="file"
            onChange={handleFileChange}
            style={{ margin: '10px 0', width: '100%' }}
          />
          <button 
            onClick={handleUpload} 
            style={{ 
              padding: '10px 20px',
              backgroundColor: '#FF5722',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              width: '100%'
            }}
          >
            Upload
          </button>
          <div style={{ marginTop: '10px' }}>{uploadMessage}</div>
        </div>
      </div>
    </div>
  );
}