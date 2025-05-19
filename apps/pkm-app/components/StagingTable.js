// File: apps/pkm-app/components/StagingTable.js
import { useEffect, useState } from 'react';

export default function StagingTable({ files, onApprove }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    setRows(files || []);
    console.log("Loaded staging files:", files);
  }, [files]);

  const handleChange = (index, field, value) => {
    const updated = [...rows];
    if (field === "tags") {
      // Handle tags as array or string
      if (typeof value === 'string') {
        updated[index].metadata.tags = value.split(",").map(t => t.trim());
      } else {
        updated[index].metadata.tags = value;
      }
    } else {
      updated[index].metadata[field] = value;
    }
    setRows(updated);
  };

  const handleApprove = async (index) => {
    const updatedFile = {
      ...rows[index],
      metadata: {
        ...rows[index].metadata,
        reviewed: true
      }
    };
    await onApprove(updatedFile);
  };

  // Helper function to ensure tags are displayed properly
  const formatTags = (tags) => {
    if (!tags) return '';
    if (Array.isArray(tags)) return tags.join(', ');
    if (typeof tags === 'string') {
      // Handle YAML formatted tags
      if (tags.startsWith('\n- ')) {
        return tags.split('\n- ').filter(t => t).join(', ');
      }
      return tags;
    }
    return String(tags);
  };

  // Helper function to get extract content
  const getExtractContent = (file) => {
    if (!file || !file.metadata) return '';
    
    // Try different possible locations for extract content
    return file.metadata.extract_content || 
           file.metadata.extract || 
           (file.content && file.content.length > 50 ? file.content.substring(0, 1000) + '...' : file.content) || 
           '';
  };

  return (
    <div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid #ddd" }}>Title</th>
            <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid #ddd" }}>Tags</th>
            <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid #ddd" }}>Category</th>
            <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid #ddd" }}>Extract</th>
            <th style={{ textAlign: "center", padding: "10px", borderBottom: "2px solid #ddd" }}>Approve</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((file, index) => (
            <tr key={index} style={{ borderBottom: "1px solid #ccc" }}>
              <td style={{ padding: "10px" }}>
                <strong>{file.metadata?.title || file.metadata?.extract_title || file.name}</strong>
              </td>
              <td style={{ padding: "10px" }}>
                <input
                  type="text"
                  value={formatTags(file.metadata?.tags)}
                  onChange={(e) => handleChange(index, "tags", e.target.value)}
                  style={{ width: "100%", padding: "5px" }}
                />
              </td>
              <td style={{ padding: "10px" }}>
                <input
                  type="text"
                  value={file.metadata?.category || ""}
                  onChange={(e) => handleChange(index, "category", e.target.value)}
                  style={{ width: "100%", padding: "5px" }}
                />
              </td>
              <td style={{ padding: "10px" }}>
                <textarea
                  value={getExtractContent(file)}
                  onChange={(e) => handleChange(index, "extract_content", e.target.value)}
                  style={{ width: "100%", height: "150px", padding: "5px" }}
                />
                {file.content && file.content.length > 1000 && (
                  <div style={{ marginTop: "5px", fontSize: "12px", color: "#666" }}>
                    <a href="#" onClick={(e) => {
                      e.preventDefault();
                      handleChange(index, "extract_content", file.content);
                    }}>
                      Load full content ({Math.round(file.content.length / 1000)}K chars)
                    </a>
                  </div>
                )}
              </td>
              <td style={{ padding: "10px", textAlign: "center" }}>
                <button 
                  onClick={() => handleApprove(index)}
                  style={{ 
                    padding: "8px 15px", 
                    backgroundColor: "#4CAF50", 
                    color: "white", 
                    border: "none", 
                    borderRadius: "4px",
                    cursor: "pointer"
                  }}
                >
                  Approve
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan="5" style={{ textAlign: "center", padding: "2rem", color: "gray" }}>
                No files found for review. If you've just processed files, they may still be being indexed.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      
      <div style={{ marginTop: "20px", fontSize: "14px", color: "#666", padding: "10px", backgroundColor: "#f9f9f9", borderRadius: "4px" }}>
        <p><strong>Tips:</strong></p>
        <ul>
          <li>Tags should be comma-separated (e.g., "AI, resources, learning")</li>
          <li>Extract can be modified before approval</li>
          <li>Click Approve when you're satisfied with the metadata</li>
        </ul>
      </div>
    </div>
  );
}