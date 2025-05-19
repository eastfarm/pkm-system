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
      updated[index].metadata.tags = value.split(",").map(t => t.trim());
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

  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th style={{ textAlign: "left" }}>Title</th>
          <th>Tags</th>
          <th>Category</th>
          <th>Summary</th>
          <th>Approve</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((file, index) => (
          <tr key={index} style={{ borderBottom: "1px solid #ccc" }}>
            <td><strong>{file.metadata?.title || file.name}</strong></td>
            <td>
              <input
                type="text"
                value={(file.metadata?.tags || []).join(', ')}
                onChange={(e) => handleChange(index, "tags", e.target.value)}
                style={{ width: "100%" }}
              />
            </td>
            <td>
              <input
                type="text"
                value={file.metadata?.category || ""}
                onChange={(e) => handleChange(index, "category", e.target.value)}
                style={{ width: "100%" }}
              />
            </td>
            <td>
              <textarea
                value={file.metadata?.summary || ""}
                onChange={(e) => handleChange(index, "summary", e.target.value)}
                style={{ width: "100%", height: "100px" }}
              />
            </td>
            <td>
              <button onClick={() => handleApprove(index)}>Approve</button>
            </td>
          </tr>
        ))}
        {rows.length === 0 && (
          <tr>
            <td colSpan="5" style={{ textAlign: "center", padding: "1rem", color: "gray" }}>
              No files found.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
