import { useState } from 'react';
import axios from 'axios';

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState('');
  const [file, setFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState('');

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
      } catch (error) {
        setUploadMessage('Upload failed: ' + error.message);
      }
    };
    reader.readAsDataURL(file);
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>PKM Query</h1>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask your KB..."
        style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
      />
      <button onClick={handleQuery} style={{ padding: '10px 20px' }}>Search</button>
      <div style={{ marginTop: '20px', whiteSpace: 'pre-wrap' }}>{results}</div>

      <h2>Upload File to Inbox</h2>
      <input
        type="file"
        onChange={handleFileChange}
        style={{ margin: '10px 0' }}
      />
      <button onClick={handleUpload} style={{ padding: '10px 20px' }}>Upload</button>
      <div style={{ marginTop: '10px' }}>{uploadMessage}</div>
    </div>
  );
}