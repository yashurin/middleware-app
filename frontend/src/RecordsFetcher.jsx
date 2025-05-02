import React, { useState } from "react";
import axios from "axios";

const RecordsFetcher = ({ schemaOptions }) => {
  const [selectedSchema, setSelectedSchema] = useState(schemaOptions[0] || "");
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [records, setRecords] = useState([]);
  const [fetchStatus, setFetchStatus] = useState("");

  const handleFetch = async () => {
    setFetchStatus("Fetching...");
    try {
      const response = await axios.get("http://localhost:8000/records", {
        params: {
          schema_name: selectedSchema,
          limit,
          offset,
        },
      });
      setRecords(response.data);
      setFetchStatus(`Fetched ${response.data.length} records`);
    } catch (error) {
      const msg =
        error.response?.data?.detail ||
        error.message ||
        "An unknown error occurred";
      setFetchStatus(`Error: ${msg}`);
    }
  };

  return (
    <div style={{ padding: "1rem", border: "1px solid #ccc", marginTop: "1rem" }}>
      <h3>Fetch Records by Schema</h3>

      <label>Schema:</label>
      <select
        value={selectedSchema}
        onChange={(e) => setSelectedSchema(e.target.value)}
      >
        {schemaOptions.map((schema) => (
          <option key={schema} value={schema}>
            {schema}
          </option>
        ))}
      </select>

      <br />

      <label>Limit:</label>
      <input
        type="number"
        min="1"
        max="100"
        value={limit}
        onChange={(e) => setLimit(Number(e.target.value))}
      />

      <label>Offset:</label>
      <input
        type="number"
        min="0"
        value={offset}
        onChange={(e) => setOffset(Number(e.target.value))}
      />

      <button onClick={handleFetch}>Fetch Records</button>

      <p>{fetchStatus}</p>

      {records.length > 0 && (
        <div>
          <h4>Records:</h4>
          <pre style={{ whiteSpace: "pre-wrap", textAlign: "left" }}>
            {JSON.stringify(records, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default RecordsFetcher;
