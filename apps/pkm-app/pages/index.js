// File: apps/pkm-app/pages/index.js
import { useState, useEffect } from 'react';
import axios from 'axios';
import Link from 'next/link';

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState('');
  const [syncStatus, setSyncStatus] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [fileStats, setFileStats] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [webhookStatus, setWebhookStatus] = useState(null);

  // Fetch file stats and webhook status when the component loads
  useEffect(() => {
    fetchFileStats();
    fetchWebhookStatus();
    
    // Set up auto-refresh every 2 minutes
    const interval = setInterval(() => {
      fetchFileStats();
      fetchWebhookStatus();
    }, 120000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchFileStats = async () => {
    try {
      const response = await axios.get('https://pkm-indexer-production.up.railway.app/file-stats');
      setFileStats(response.data);
    } catch (error) {
      console.error('Failed to fetch file stats:', error);
    }
  };

  const fetchWebhookStatus = async () => {
    try {
      const response = await axios.get('https://pkm-indexer-production.up.railway.app/webhook/status');
      setWebhookStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch webhook status:', error);
      setWebhookStatus(null);
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

  const triggerOrganize = async () => {
    try {
      const response = await axios.post('https://pkm-indexer-production.up.railway.app/trigger-organize');
      alert(`${response.data.status}`);
      // Refresh file stats after organizing
      fetchFileStats();
    } catch (error) {
      alert(`Failed: ${error.message}`);
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
      
      {/* Main action button */}
      <div style={{ 
        marginBottom: '30px', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center',
        backgroundColor: '#f8f9fa', 
        padding: '20px',
        borderRadius: '8px',
        border: '1px solid #e9ecef'
      }}>
        <h2 style={{ marginTop: '0', marginBottom: '15px', textAlign: 'center' }}>Google Drive Integration</h2>
        
        {/* Auto-sync Status Badge */}
        <div style={{ 
          marginBottom: '15px', 
          padding: '8px 15px', 
          backgroundColor: webhookStatus?.is_active ? '#e8f5e9' : '#fff3e0', 
          borderRadius: '4px',
          border: `1px solid ${webhookStatus?.is_active ? '#a5d6a7' : '#ffe0b2'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          maxWidth: '500px',
          fontSize: '15px'
        }}>
          {webhookStatus?.is_active ? (
            <span>
              ✅ Automatic synchronization is active. Files added to Google Drive will be processed immediately.
            </span>
          ) : (
            <span>
              ⚠️ Setting up automatic synchronization... This will be active shortly.
            </span>
          )}
        </div>
        
        <button 
          onClick={triggerDriveSync} 
          disabled={isSyncing}
          style={{ 
            padding: '15px 25px', 
            backgroundColor: isSyncing ? '#ccc' : '#2196F3', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: isSyncing ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
            width: '100%',
            maxWidth: '300px'
          }}
        >
          {isSyncing ? 'Syncing...' : 'Sync Now'}
        </button>
        
        {/* Sync status message */}
        {syncStatus && (
          <div style={{ 
            marginTop: '15px', 
            padding: '10px', 
            backgroundColor: syncStatus.includes('✅') ? '#e8f5e9' : 
                             syncStatus.includes('ℹ️') ? '#e3f2fd' : '#ffebee',
            borderRadius: '4px',
            width: '100%',
            maxWidth: '500px',
            textAlign: 'center'
          }}>
            {syncStatus}
          </div>
        )}
        
        <div style={{ fontSize: '13px', color: '#666', marginTop: '20px', textAlign: 'center' }}>
          <p>Place files in your Google Drive's <strong>PKM/Inbox</strong> folder to process them automatically.</p>
          <p>The "Sync Now" button manually checks for new files if you don't want to wait for auto-sync.</p>
        </div>
      </div>

      {/* System Stats */}
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
                {fileStats.source_types ? Object.entries(fileStats.source_types).map(([type, count], index) => (
                  <span key={type}>
                    {index > 0 && ', '}
                    {type}: {count}
                  </span>
                )) : 'None'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div style={{ 
        display: 'flex', 
        gap: '20px', 
        marginBottom: '30px',
        flexWrap: 'wrap'
      }}>
        {/* Navigation */}
        <div style={{ flex: '1', minWidth: '300px' }}>
          <h2>Navigation</h2>
          <ul style={{ listStyleType: 'none', padding: '0' }}>
            <li style={{ margin: '10px 0' }}>
              <Link href="/staging" style={{ 
                display: 'block',
                padding: '12px', 
                backgroundColor: '#f0f0f0', 
                borderRadius: '4px',
                color: '#333',
                textDecoration: 'none',
                fontWeight: 'bold'
              }}>
                🔍 Review Staging Files
              </Link>
            </li>
            <li style={{ margin: '10px 0' }}>
              <a href="https://pkm-indexer-production.up.railway.app/logs" target="_blank" rel="noopener noreferrer" style={{ 
                display: 'block',
                padding: '12px', 
                backgroundColor: '#f0f0f0', 
                borderRadius: '4px',
                color: '#333',
                textDecoration: 'none',
                fontWeight: 'bold'
              }}>
                📋 View Processing Logs
              </a>
            </li>
          </ul>
          
          {/* Advanced controls (hidden by default) */}
          <div style={{ marginTop: '20px' }}>
            <button 
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{ 
                backgroundColor: 'transparent',
                border: 'none',
                color: '#666',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: '5px 0'
              }}
            >
              {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
            </button>
            
            {showAdvanced && (
              <div style={{ 
                marginTop: '10px',
                padding: '15px',
                backgroundColor: '#f5f5f5',
                borderRadius: '4px'
              }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 10px 0' }}>Advanced Controls</h3>
                <button 
                  onClick={triggerOrganize}
                  style={{ 
                    padding: '8px 15px',
                    backgroundColor: '#9e9e9e',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Process Local Files
                </button>
                <p style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>
                  Only use this if you've manually placed files in the local inbox.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Query section */}
        <div style={{ flex: '1', minWidth: '300px' }}>
          <h2>Query Knowledge Base</h2>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask your KB..."
            style={{ 
              width: '100%', 
              padding: '12px', 
              marginBottom: '10px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
          <button 
            onClick={handleQuery} 
            style={{ 
              padding: '12px 20px',
              backgroundColor: '#673AB7',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
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
      </div>
    </div>
  );
}