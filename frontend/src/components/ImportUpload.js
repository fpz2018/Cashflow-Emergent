import React, { useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ImportUpload = ({ onPreviewReady }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [importType, setImportType] = useState('epd_declaraties');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const importTypes = [
    { 
      value: 'epd_declaraties', 
      label: 'EPD Declaraties',
      description: 'CSV met kolommen: factuur, datum, verzekeraar, bedrag',
      example: 'INV001, 2025-01-15, CZ, 150.50'
    },
    { 
      value: 'epd_particulier', 
      label: 'EPD Particuliere Facturen',
      description: 'CSV met kolommen: factuur, datum, debiteur, bedrag',
      example: 'INV002, 2025-01-15, Jan de Vries, 75.00'
    },
    { 
      value: 'bank_bunq', 
      label: 'BUNQ Bank Export',
      description: 'BUNQ CSV export voor reconciliatie',
      example: 'Date, Amount, Counterparty, Description'
    }
  ];

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = (file) => {
    if (!file.name.endsWith('.csv')) {
      setError('Alleen CSV bestanden zijn toegestaan');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      setError('Bestand te groot. Maximum 10MB toegestaan');
      return;
    }

    setSelectedFile(file);
    setError('');
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handlePreview = async () => {
    if (!selectedFile) {
      setError('Selecteer eerst een bestand');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // First, inspect the file columns for better debugging
      const inspectFormData = new FormData();
      inspectFormData.append('file', selectedFile);
      
      const inspectResponse = await axios.post(`${API}/import/inspect-columns`, inspectFormData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('File inspection:', inspectResponse.data);

      // Then proceed with preview
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('import_type', importType);

      const response = await axios.post(`${API}/import/preview`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Add file and import type to preview data for later execution
      const previewDataWithFile = {
        ...response.data,
        originalFile: selectedFile,
        originalImportType: importType
      };

      onPreviewReady(previewDataWithFile);
    } catch (error) {
      console.error('Preview error:', error);
      
      // Try to provide more helpful error messages
      let errorMessage = error.response?.data?.detail || 'Fout bij verwerken bestand';
      
      if (errorMessage.includes('kolom niet gevonden')) {
        errorMessage += `\n\nTip: Controleer of uw CSV bestand de juiste kolomnamen heeft:
        
Voor BUNQ bestanden verwachten we kolommen zoals:
• Datum/Date (voor datum)
• Bedrag/Amount (voor bedrag)  
• Tegenpartij/Counterparty (optioneel)
• Omschrijving/Description (optioneel)`;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Import Type Selection */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">Selecteer Import Type</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {importTypes.map((type) => (
            <div
              key={type.value}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                importType === type.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
              onClick={() => setImportType(type.value)}
              data-testid={`import-type-${type.value}`}
            >
              <div className="flex items-center mb-2">
                <input
                  type="radio"
                  name="importType"
                  value={type.value}
                  checked={importType === type.value}
                  onChange={() => setImportType(type.value)}
                  className="mr-3 text-blue-600"
                />
                <h4 className="font-medium text-slate-900">{type.label}</h4>
              </div>
              <p className="text-sm text-slate-600 mb-2">{type.description}</p>
              <p className="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-1 rounded">
                {type.example}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* File Upload Area */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">Upload CSV Bestand</h3>
        </div>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-slate-300 hover:border-slate-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          data-testid="file-drop-zone"
        >
          {selectedFile ? (
            <div className="space-y-4">
              <div className="flex items-center justify-center w-16 h-16 mx-auto bg-green-100 rounded-full">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              
              <div>
                <p className="text-lg font-medium text-slate-900">{selectedFile.name}</p>
                <p className="text-slate-600">{formatFileSize(selectedFile.size)}</p>
                <p className="text-sm text-green-600 mt-2">✓ Bestand geselecteerd</p>
              </div>
              
              <button
                onClick={() => setSelectedFile(null)}
                className="text-sm text-slate-500 hover:text-slate-700 underline"
                data-testid="remove-file-button"
              >
                Ander bestand selecteren
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-center w-16 h-16 mx-auto bg-slate-100 rounded-full">
                <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              
              <div>
                <p className="text-lg text-slate-700 mb-2">
                  Sleep uw CSV bestand hierheen of
                </p>
                <label className="cursor-pointer">
                  <span className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-block">
                    Bestand Selecteren
                  </span>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileInputChange}
                    className="hidden"
                    data-testid="file-input"
                  />
                </label>
              </div>
              
              <p className="text-sm text-slate-500">
                Ondersteunde formaten: CSV (max 10MB)
              </p>
            </div>
          )}
        </div>

        {error && (
          <div className="error-state mt-4" data-testid="upload-error">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h4 className="font-medium text-red-800 mb-1">Import fout</h4>
                <div className="text-sm text-red-700 whitespace-pre-line">{error}</div>
              </div>
            </div>
          </div>
        )}

        {selectedFile && (
          <div className="flex justify-end mt-6">
            <button
              onClick={handlePreview}
              disabled={loading}
              className={`px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation ${
                loading ? 'opacity-70 cursor-not-allowed' : 'hover:from-blue-700 hover:to-indigo-700'
              }`}
              data-testid="preview-button"
            >
              {loading ? (
                <>
                  <div className="spinner w-4 h-4 mr-2 inline-block"></div>
                  Verwerken...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  Voorbeeld Bekijken
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Import Instructions */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">Import Instructies</h3>
        </div>
        
        <div className="space-y-4 text-sm text-slate-600">
          <div>
            <h4 className="font-medium text-slate-800 mb-2">EPD Declaraties Format:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Kolommen:</strong> factuur, datum, verzekeraar, bedrag</li>
              <li><strong>Datum format:</strong> 8-1-2025 (dag-maand-jaar)</li>
              <li><strong>Bedrag format:</strong> € 824,65 of € 1.646,30 (met Euro symbool en komma)</li>
              <li><strong>Verzekeraar:</strong> Automatische cleaning van factuur prefixen</li>
            </ul>
            <div className="mt-2 p-2 bg-green-50 rounded text-xs text-green-700">
              <strong>✅ Compatible:</strong> Gebruikt puntkomma delimiter en Nederlandse formats
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-slate-800 mb-2">EPD Particuliere Facturen Format:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Kolommen:</strong> factuur, datum, debiteur, bedrag</li>
              <li><strong>Datum format:</strong> 8-1-2025 (dag-maand-jaar)</li>
              <li><strong>Bedrag format:</strong> € 75,00 of € 1.250,50 (met Euro symbool en komma)</li>
              <li><strong>Debiteur:</strong> Naam van de particuliere patiënt</li>
            </ul>
            <div className="mt-2 p-2 bg-green-50 rounded text-xs text-green-700">
              <strong>✅ Compatible:</strong> Zelfde format als EPD declaraties met puntkomma delimiter
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-slate-800 mb-2">BUNQ Bank Export:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li>BUNQ CSV transactieoverzicht export</li>
              <li>Gebruikt voor bank reconciliatie en cashflow matching</li>
              <li><strong>Verwachte kolommen:</strong> datum, debiteur, omschrijving, bedrag</li>
              <li><strong>Datum format:</strong> 1-1-2025 (dag-maand-jaar)</li>
              <li><strong>Bedrag format:</strong> € -89,75 of € 124,76 (met Euro symbool en komma)</li>
            </ul>
            <div className="mt-2 p-2 bg-green-50 rounded text-xs text-green-700">
              <strong>✅ Compatible:</strong> Gebruikt exacte BUNQ export format met puntkomma delimiter
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImportUpload;