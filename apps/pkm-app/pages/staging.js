import { useState, useEffect } from 'react';
import axios from 'axios';
import StagingTable from '../components/StagingTable';

export default function Staging() {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await axios.get('https://pkm-indexer-production.up.railway.app/staging');
      setFiles(response.data.files || []);
    } catch (err) {
      setError('Failed to load staging files');
    }
  };

  const handleApprove = async (file) => {
    try {
      await axios.post('https://pkm-indexer-production.up.railway.app/approve', { file });
      fetchFiles();
    } catch (err) {
      setError('Failed to approve file');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1>Review Staging Files</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <StagingTable files={files} onApprove={handleApprove} />
    </div>
  );
}
