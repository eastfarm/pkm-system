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
        reviewed: true,
        reprocess_status: "none"
      }
    };
    await onApprove(updatedFile);
  };

  const handleReprocess = async (index) => {
    const updatedFile = {
      ...rows[index],
      metadata: {
        ...rows[index].metadata,
        reprocess_status: "requested",
        reprocess_rounds: (parseInt(rows[index].metadata.reprocess_rounds || 0) + 1).toString()
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
    
    // First try getting the exact extract_content field
    if (file.metadata.extract_content && file.metadata.extract_content.length > 10) {
      return file.metadata.extract_content;
    }
    
    // Fall back to extract field
    if (file.metadata.extract && file.metadata.extract.length > 10) {
      return file.metadata.extract;
    }
    
    // Fall back to first 1000 chars of file content
    if (file.content && file.content.length > 50) {
      return file.content.substring(0, 1000) + (file.content.length > 1000 ? '...' : '');
    }
    
    return 'No extract available';
  };

  const tableStyle = {
    width: "100%", 
    borderCollapse: "collapse",
    tableLayout: "fixed"  // Fixed layout for better column control
  };

  const thStyle = {
    textAlign: "left", 
    padding: "8px", 
    borderBottom: "2px solid #ddd",
    backgroundColor: "#f5f5f5",
    fontSize: "14px"
  };

  const cellStyle = {
    padding: "8px",
    verticalAlign: "top",
    borderBottom: "1px solid #ddd"
  };

  return (
    <div>
      <table style={tableStyle}>
        <colgroup>
          <col style={{ width: "20%" }} /> {/* Title */}
          <col style={{ width: "10%" }} /> {/* Category */}
          <col style={{ width: "15%" }} /> {/* Tags */}
          <col style={{ width: "45%" }} /> {/* Extract */}
          <col style={{ width: "10%" }} /> {/* Actions */}
        </colgroup>
        <thead>
          <tr>
            <th style={thStyle}>Title</th>
            <th style={thStyle}>Category</th>
            <th style={thStyle}>Tags</th>
            <th style={thStyle}>Extract</th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((file, index) => (
            <tr key={index} style={{ borderBottom: "1px solid #eee" }}>
              <td style={cellStyle}>
                <input
                  type="text"
                  value={file.metadata?.title || file.metadata?.extract_title || file.name}
                  onChange={(e) => handleChange(index, "title", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "4px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    fontSize: "14px"
                  }}
                />
                <div style={{ 
                  fontSize: "12px", 
                  color: "#666", 
                  marginTop: "4px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis"
                }}>
                  {file.name}
                </div>
              </td>
              <td style={cellStyle}>
                <select
                  value={file.metadata?.category || ""}
                  onChange={(e) => handleChange(index, "category", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "4px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    backgroundColor: "white"
                  }}
                >
                  <option value="">Select...</option>
                  <option value="Reference">Reference</option>
                  <option value="Note">Note</option>
                  <option value="Image">Image</option>
                  <option value="LinkedIn Post">LinkedIn Post</option>
                  <option value="Resource List">Resource List</option>
                  <option value="Book">Book</option>
                  <option value="Article">Article</option>
                  <option value="Paper">Paper</option>
                </select>
              </td>
              <td style={cellStyle}>
                <input
                  type="text"
                  value={formatTags(file.metadata?.tags)}
                  onChange={(e) => handleChange(index, "tags", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "4px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    fontSize: "14px"
                  }}
                  placeholder="tag1, tag2, tag3"
                />
              </td>
              <td style={cellStyle}>
                <textarea
                  value={getExtractContent(file)}
                  onChange={(e) => handleChange(index, "extract_content", e.target.value)}
                  style={{
                    width: "100%",
                    height: "200px",
                    padding: "8px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    fontSize: "14px",
                    lineHeight: "1.4"
                  }}
                />
                
                <div style={{ marginTop: "8px" }}>
                  <label style={{ 
                    display: "block", 
                    fontSize: "13px", 
                    fontWeight: "bold",
                    marginBottom: "4px"
                  }}>
                    Reprocess Notes:
                  </label>
                  <textarea
                    value={file.metadata?.reprocess_notes || ""}
                    onChange={(e) => handleChange(index, "reprocess_notes", e.target.value)}
                    placeholder="Add notes for reprocessing (e.g., 'This is a quote, just extract key ideas')"
                    style={{
                      width: "100%",
                      height: "60px",
                      padding: "4px",
                      border: "1px solid #ddd",
                      borderRadius: "4px",
                      fontSize: "13px"
                    }}
                  />
                </div>
              </td>
              <td style={{...cellStyle, textAlign: "center"}}>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <button 
                    onClick={() => handleApprove(index)}
                    style={{ 
                      padding: "8px", 
                      backgroundColor: "#4CAF50", 
                      color: "white", 
                      border: "none", 
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "14px"
                    }}
                  >
                    Save
                  </button>
                  <button 
                    onClick={() => handleReprocess(index)}
                    style={{ 
                      padding: "8px", 
                      backgroundColor: "#2196F3", 
                      color: "white", 
                      border: "none", 
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "14px"
                    }}
                  >
                    Reprocess
                  </button>
                </div>
                
                <div style={{ 
                  marginTop: "10px", 
                  fontSize: "12px", 
                  color: "#666" 
                }}>
                  Status: {file.metadata?.reprocess_status || "none"}
                  {file.metadata?.reprocess_rounds && 
                    <div>Rounds: '{file.metadata.reprocess_rounds}'</div>
                  }
                </div>
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
      
      <div style={{ 
        marginTop: "20px", 
        fontSize: "14px", 
        color: "#666", 
        padding: "15px", 
        backgroundColor: "#f9f9f9", 
        borderRadius: "4px",
        display: "flex",
        justifyContent: "space-between"
      }}>
        <div>
          <strong>Save</strong>: Finalize the current extract and metadata.
        </div>
        <div>
          <strong>Reprocess</strong>: Request AI to regenerate the extract with your notes.
        </div>
        <div>
          <strong>Tags</strong>: Comma-separated values.
        </div>
      </div>
    </div>
  );
}