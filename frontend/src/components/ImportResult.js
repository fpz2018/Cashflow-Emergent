import React from 'react';

const ImportResult = ({ result, onBack }) => {
  if (!result) {
    return null;
  }

  const { success, imported_count, error_count, errors = [] } = result;

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Import Resultaten</h3>
          <p className="text-slate-600">
            Import {success ? 'succesvol' : 'mislukt'}
          </p>
        </div>
        
        <button
          onClick={onBack}
          className="px-4 py-2 text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
          data-testid="back-to-upload"
        >
          ← Nieuwe Import
        </button>
      </div>

      {/* Result Summary */}
      <div className="modern-card">
        <div className="text-center py-8">
          {success ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              
              <div>
                <h4 className="text-2xl font-bold text-green-600 mb-2">
                  {imported_count} rijen geïmporteerd
                </h4>
                <p className="text-slate-600">
                  Import succesvol voltooid
                </p>
              </div>
              
              {error_count > 0 && (
                <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-amber-700">
                    <strong>Let op:</strong> {error_count} rijen overgeslagen wegens fouten
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              
              <div>
                <h4 className="text-2xl font-bold text-red-600 mb-2">
                  Import mislukt
                </h4>
                <p className="text-slate-600">
                  Er zijn fouten opgetreden tijdens de import
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Details */}
      {errors.length > 0 && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">Fout Details</h4>
            <span className="text-sm text-slate-500">{errors.length} fouten</span>
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {errors.map((error, index) => (
              <div 
                key={index}
                className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
              >
                {error}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="modern-card text-center">
          <div className="text-2xl font-bold text-green-600">{imported_count}</div>
          <div className="text-sm text-slate-600">Succesvol Geïmporteerd</div>
        </div>
        
        <div className="modern-card text-center">
          <div className="text-2xl font-bold text-red-600">{error_count}</div>
          <div className="text-sm text-slate-600">Fouten</div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-center pt-6 border-t border-slate-200">
        <button
          onClick={onBack}
          className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation hover:from-blue-700 hover:to-indigo-700"
          data-testid="new-import-button"
        >
          Nieuwe Import
        </button>
      </div>
    </div>
  );
};

export default ImportResult;