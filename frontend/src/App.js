import React from 'react';
import SchemaUploadForm from './SchemaUploadForm';
import RecordsFetcher from "./RecordsFetcher";

const schemaOptions = ["contact-message-schema", "schema2", "schema3"]; // Can be refactored later to fetch from API


function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <SchemaUploadForm />
      <RecordsFetcher schemaOptions={schemaOptions} />
    </div>
  );
}

export default App;
