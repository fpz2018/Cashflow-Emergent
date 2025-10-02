import React, { useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CopyPasteImport = ({ onRefresh }) => {
  const [activeImportType, setActiveImportType] = useState('verzekeraars');
  const [pasteData, setPasteData] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const importTypes = {
    verzekeraars: {
      label: 'Verzekeraars',
      description: 'Importeer verzekeraars met hun betaaltermijnen',
      columns: 'naam, termijn',
      example: 'CZ Zorgverzekeraar\t30\nVGZ\t45\nZilveren Kruis\t21',
      placeholder: `Plak hier uw verzekeraars data:
CZ Zorgverzekeraar	30
VGZ	45  
Zilveren Kruis	21`
    },
    crediteuren: {
      label: 'Crediteuren',
      description: 'Importeer crediteuren met vaste betalingen',
      columns: 'crediteur, bedrag, dag',
      example: 'Huur Praktijk\t€ 1.200,00\t1\nNetto Salarissen\t€ 12.500,00\t25\nElektra\t150,50\t15',
      placeholder: `Plak hier uw crediteuren data:
Huur Praktijk	€ 1.200,00	1
Netto Salarissen	€ 12.500,00	25
Elektra	150,50	15`
    }
  };

  const handlePreview = async () => {
    if (!pasteData.trim()) {
      setError('Voer data in om te importeren');
      return;
    }

    setLoading(true);
    setError('');
    setPreviewData(null);

    try {
      const response = await axios.post(`${API}/copy-paste-import/preview`, {
        data: pasteData,
        import_type: activeImportType
      });

      setPreviewData(response.data);
    } catch (error) {
      console.error('Preview error:', error);
      setError(error.response?.data?.detail || 'Fout bij verwerken data');
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!previewData) return;

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/copy-paste-import/execute`, {
        data: pasteData,
        import_type: activeImportType
      });

      setImportResult(response.data);
      setPreviewData(null);
      onRefresh && onRefresh();
    } catch (error) {
      console.error('Import error:', error);
      setError(error.response?.data?.detail || 'Fout bij importeren');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setPasteData('');
    setPreviewData(null);
    setImportResult(null);
    setError('');
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const currentImportType = importTypes[activeImportType];

  if (importResult) {
    return (
      <div className="space-y-6 fade-in">
        {/* Success Result */}
        <div className="modern-card">
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            
            <h3 className="text-2xl font-bold text-green-600 mb-2">
              {importResult.imported_count} {currentImportType.label.toLowerCase()} geïmporteerd
            </h3>
            <p className="text-slate-600 mb-6">
              Import succesvol voltooid
            </p>
            
            <button
              onClick={resetForm}
              className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation hover:from-blue-700 hover:to-indigo-700"
            >
              Nieuwe Import
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 gradient-text">
          Copy & Paste Import
        </h2>
        <p className="text-slate-600 mt-1">
          Importeer verzekeraars en crediteuren via copy & paste
        </p>
      </div>

      {/* Import Type Selection */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">Selecteer Import Type</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(importTypes).map(([key, type]) => (
            <div
              key={key}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                activeImportType === key
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
              onClick={() => setActiveImportType(key)}
            >
              <div className="flex items-center mb-2">
                <input
                  type="radio"
                  name="importType"
                  value={key}
                  checked={activeImportType === key}
                  onChange={() => setActiveImportType(key)}
                  className="mr-3 text-blue-600"
                />
                <h4 className="font-medium text-slate-900">{type.label}</h4>
              </div>
              <p className="text-sm text-slate-600 mb-2">{type.description}</p>
              <p className="text-xs text-slate-500">
                <strong>Kolommen:</strong> {type.columns}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Copy Paste Area */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">
            {currentImportType.label} Data
          </h3>
        </div>

        <div className="space-y-4">
          <textarea
            value={pasteData}
            onChange={(e) => setPasteData(e.target.value)}
            placeholder={currentImportType.placeholder}
            rows={8}
            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-none"
          />
          
          <div className="bg-slate-50 p-4 rounded-lg">
            <h4 className="font-medium text-slate-800 mb-2">Instructies:</h4>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>• Data kan gescheiden zijn door tabs, spaties of puntkomma's</li>
              <li>• Elke rij op een nieuwe regel</li>
              <li>• Kolommen: <code className="bg-slate-200 px-1 rounded">{currentImportType.columns}</code></li>
              {activeImportType === 'verzekeraars' && (
                <li>• <strong>Termijn:</strong> aantal dagen (bijv. 30, 45, 60)</li>
              )}
              {activeImportType === 'crediteuren' && (
                <>
                  <li>• <strong>Bedrag:</strong> maandbedrag (bijv. 1200, 150.50)</li>
                  <li>• <strong>Dag:</strong> dag van de maand 1-31 (bijv. 1, 15, 28)</li>
                </>
              )}
            </ul>
          </div>

          {error && (
            <div className="error-state">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end mt-6 gap-3">
          <button
            onClick={() => setPasteData('')}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
          >
            Wissen
          </button>
          
          <button
            onClick={handlePreview}
            disabled={loading || !pasteData.trim()}
            className={`px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation ${
              loading || !pasteData.trim() ? 'opacity-70 cursor-not-allowed' : 'hover:from-blue-700 hover:to-indigo-700'
            }`}
          >
            {loading ? (
              <>
                <div className="spinner w-4 h-4 mr-2 inline-block"></div>
                Verwerken...
              </>
            ) : (
              'Preview'
            )}
          </button>
        </div>
      </div>

      {/* Preview Results */}
      {previewData && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h3 className="text-lg font-semibold text-slate-900">Preview Resultaten</h3>
            <div className="text-sm text-slate-600">
              {previewData.imported_count} geldig, {previewData.error_count} fouten
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                  {activeImportType === 'verzekeraars' && (
                    <>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Verzekeraar
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Termijn (dagen)
                      </th>
                    </>
                  )}
                  {activeImportType === 'crediteuren' && (
                    <>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Crediteur
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Bedrag
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Dag v/d Maand
                      </th>
                    </>
                  )}
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Fouten
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {previewData.preview_data.map((item, index) => (
                  <tr 
                    key={index}
                    className={item.import_status === 'valid' ? 'bg-green-50' : 'bg-red-50'}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.import_status === 'valid' ? (
                        <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      )}
                    </td>
                    
                    {activeImportType === 'verzekeraars' && (
                      <>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                          {item.mapped_data?.naam || '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                          {item.mapped_data?.termijn ? `${item.mapped_data.termijn} dagen` : '-'}
                        </td>
                      </>
                    )}
                    
                    {activeImportType === 'crediteuren' && (
                      <>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                          {item.mapped_data?.crediteur || '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                          {item.mapped_data?.bedrag ? formatCurrency(item.mapped_data.bedrag) : '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                          {item.mapped_data?.dag ? `${item.mapped_data.dag}e` : '-'}
                        </td>
                      </>
                    )}
                    
                    <td className="px-4 py-3 text-sm text-red-600">
                      {item.validation_errors?.join(', ') || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {previewData.imported_count > 0 && (
            <div className="flex justify-end mt-6 pt-4 border-t border-slate-200">
              <button
                onClick={handleImport}
                disabled={loading}
                className={`px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation ${
                  loading ? 'opacity-70 cursor-not-allowed' : 'hover:from-green-700 hover:to-emerald-700'
                }`}
              >
                {loading ? (
                  <>
                    <div className="spinner w-4 h-4 mr-2 inline-block"></div>
                    Importeren...
                  </>
                ) : (
                  <>
                    Importeer {previewData.imported_count} {currentImportType.label.toLowerCase()}
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CopyPasteImport;