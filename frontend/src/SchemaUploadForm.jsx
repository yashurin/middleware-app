import React, { useState } from 'react';
import axios from 'axios';

const schemas = [
  { label: 'Contact Message Schema', value: 'contact-message-schema' },
  { label: 'Product Schema', value: 'product' },
  { label: 'Order Schema', value: 'order' }
];

const SchemaUploadForm = () => {
  const [selectedSchema, setSelectedSchema] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSchemaChange = (e) => {
    setSelectedSchema(e.target.value);
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedSchema || !selectedFile) {
      setStatusMessage('Please select a schema and a file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setLoading(true);
      const response = await axios.post(`http://localhost:8000/upload/${selectedSchema}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setStatusMessage(`Success: ${response.data.message || 'File uploaded successfully.'}`);
    } catch (error) {
        const message =
        error.response?.data?.detail ||
        error.message ||
        "An unknown error occurred.";
        setStatusMessage(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "1rem", border: "1px solid #ccc", marginTop: "1rem" }}>
      <h3>Upload File with Schema</h3>

      <div className="mb-4">
        <label className="block mb-1 font-medium">Select Schema:</label>
        <select
          value={selectedSchema}
          onChange={handleSchemaChange}
          className="w-full border rounded p-2"
        >
          <option value="">-- Select a schema --</option>
          {schemas.map((schema) => (
            <option key={schema.value} value={schema.value}>
              {schema.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="block mb-1 font-medium">Choose File:</label>
        <input
          type="file"
          onChange={handleFileChange}
          className="w-full"
        />
      </div>

      <button
        onClick={handleUpload}
        disabled={loading}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Uploading...' : 'Upload'}
      </button>

      {statusMessage && (
        <p className="mt-4 text-sm text-gray-700">{statusMessage}</p>
      )}
    </div>
  );
};

export default SchemaUploadForm;
