import React, { useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ImportPreview = ({ previewData, onComplete, onBack }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Safety check for previewData
  if (!previewData) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-slate-500">Geen preview data beschikbaar</div>
      </div>
    );
  }

  const getImportTypeLabel = (type) => {
    const labels = {
      epd_declaraties: 'EPD Declaraties',
      epd_particulier: 'EPD Particuliere Facturen',
      bank_bunq: 'BUNQ Bank Export'
    };
    return labels[type] || type;
  };

  const getStatusIcon = (status) => {
    if (status === 'valid') {
      return (
        <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      );
    } else {
      return (
        <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('nl-NL');
  };

  const handleImport = async () => {
    setLoading(true);
    setError('');

    try {
      // Check if we have the original file and import type
      if (!previewData?.originalFile || !previewData?.originalImportType) {
        throw new Error('Origineel bestand niet beschikbaar voor import');
      }

      // Re-upload the file for execution
      const formData = new FormData();
      formData.append('file', previewData.originalFile);
      formData.append('import_type', previewData.originalImportType);

      const response = await axios.post(`${API}/import/execute`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      onComplete(response.data);
    } catch (error) {
      console.error('Import error:', error);
      setError(error.response?.data?.detail || 'Fout bij importeren');
    } finally {
      setLoading(false);
    }
  };

  const canProceed = previewData?.valid_rows > 0;
  const previewItems = previewData?.preview_items || [];

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Import Voorbeeld</h3>
          <p className="text-slate-600">
            {getImportTypeLabel(previewData?.import_type)} - {previewData?.file_name || 'Onbekend bestand'}
          </p>
        </div>
        
        <button
          onClick={onBack}
          className="px-4 py-2 text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
          data-testid="back-button"
        >
          ← Terug
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="modern-card text-center">
          <div className="text-2xl font-bold text-slate-900">{previewData?.total_rows || 0}</div>
          <div className="text-sm text-slate-600">Totaal Rijen</div>
        </div>
        
        <div className="modern-card text-center">
          <div className="text-2xl font-bold text-green-600">{previewData?.valid_rows || 0}</div>
          <div className="text-sm text-slate-600">Geldige Rijen</div>
        </div>
        
        <div className="modern-card text-center">
          <div className="text-2xl font-bold text-red-600">{previewData?.error_rows || 0}</div>
          <div className="text-sm text-slate-600">Fout Rijen</div>
        </div>
      </div>

      {/* Data Preview */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h4 className="text-lg font-semibold text-slate-900">Data Voorbeeld</h4>
          <p className="text-sm text-slate-600">
            Toont eerste {Math.min(previewItems.length, 20)} rijen van {previewData?.total_rows || 0} totaal
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Rij
                </th>
                {previewData?.import_type !== 'bank_bunq' && (
                  <>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Factuur
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Datum
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      {previewData?.import_type === 'epd_declaraties' ? 'Verzekeraar' : 'Debiteur'}
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Bedrag
                    </th>
                  </>
                )}
                {previewData?.import_type === 'bank_bunq' && (
                  <>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Datum
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Bedrag
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Tegenpartij
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Omschrijving
                    </th>
                  </>
                )}
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Fouten
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {previewItems.map((item, index) => (
                <tr 
                  key={index}
                  className={item?.import_status === 'valid' ? 'bg-green-50' : 'bg-red-50'}
                  data-testid={`preview-row-${index}`}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(item?.import_status)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                    {item?.row_number || '-'}
                  </td>
                  {previewData?.import_type !== 'bank_bunq' && (
                    <>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.invoice_number || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.date ? formatDate(item.mapped_data.date) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.patient_name || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.amount ? formatCurrency(item.mapped_data.amount) : '-'}
                      </td>
                    </>
                  )}
                  {previewData?.import_type === 'bank_bunq' && (
                    <>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.date ? formatDate(item.mapped_data.date) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.amount ? formatCurrency(item.mapped_data.amount) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {item?.mapped_data?.counterparty || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900 max-w-xs truncate">
                        {item?.mapped_data?.description || '-'}
                      </td>
                    </>
                  )}
                  <td className="px-4 py-3 text-sm text-red-600">
                    {item?.validation_errors?.join(', ') || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {previewItems.length < (previewData?.total_rows || 0) && (
          <div className="p-4 bg-blue-50 border-t border-blue-200 text-center text-sm text-blue-700">
            <strong>ℹ️ Preview toont alleen eerste {previewItems.length} rijen</strong>
            <br />
            Bij import worden alle {previewData?.total_rows || 0} rijen verwerkt ({previewData?.valid_rows || 0} geldig, {previewData?.error_rows || 0} fouten)
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-state" data-testid="import-error">
          {error}
        </div>
      )}

      {/* All Errors Display */}
      {previewData?.all_errors && previewData.all_errors.length > 0 && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">Alle Import Fouten</h4>
            <span className="text-sm text-slate-500">
              {previewData.all_errors.length} van {previewData?.error_rows || 0} fouten
            </span>
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {previewData.all_errors.map((errorMsg, index) => (
              <div 
                key={index}
                className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
              >
                {errorMsg}
              </div>
            ))}
            
            {previewData.all_errors.length < (previewData?.error_rows || 0) && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 text-center">
                En nog {(previewData?.error_rows || 0) - previewData.all_errors.length} fouten...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between items-center pt-6 border-t border-slate-200">
        <div className="text-sm text-slate-600">
          {canProceed ? (
            <div className="space-y-1">
              <div className="text-green-600 font-medium">
                ✓ Klaar voor import: {previewData?.valid_rows || 0} geldige rijen
              </div>
              {(previewData?.error_rows || 0) > 0 && (
                <div className="text-amber-600">
                  ⚠️ {previewData?.error_rows || 0} rijen worden overgeslagen (fouten)
                </div>
              )}
            </div>
          ) : (
            <span className="text-red-600">
              ✗ Geen geldige rijen om te importeren
            </span>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onBack}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
            data-testid="cancel-import-button"
          >
            Annuleren
          </button>
          
          <button
            onClick={handleImport}
            disabled={loading || !canProceed}
            className={`px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation ${
              loading || !canProceed ? 'opacity-70 cursor-not-allowed' : 'hover:from-green-700 hover:to-emerald-700'
            }`}
            data-testid="confirm-import-button"
          >
            {loading ? (
              <>
                <div className="spinner w-4 h-4 mr-2 inline-block"></div>
                Importeren...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Import Uitvoeren ({previewData?.valid_rows || 0} rijen)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportPreview;