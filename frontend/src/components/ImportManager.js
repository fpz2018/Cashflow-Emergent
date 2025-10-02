import React, { useState } from 'react';
import ImportUpload from './ImportUpload';
import ImportPreview from './ImportPreview';
import ImportResult from './ImportResult';
import CopyPasteImport from './CopyPasteImport';
import BankReconciliation from './BankReconciliation';

const ImportManager = ({ onRefresh }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [previewData, setPreviewData] = useState(null);
  const [importResult, setImportResult] = useState(null);

  const tabs = [
    { id: 'upload', label: 'Bestanden Uploaden', icon: 'upload' },
    { id: 'copypaste', label: 'Copy & Paste', icon: 'clipboard' },
    { id: 'reconciliation', label: 'Bank Reconciliatie', icon: 'link' }
  ];

  const getIcon = (iconName) => {
    const icons = {
      upload: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      link: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      )
    };
    return icons[iconName];
  };

  const handlePreviewComplete = (result) => {
    setImportResult(result);
    setPreviewData(null);
    onRefresh && onRefresh();
  };

  const handleBackToUpload = () => {
    setPreviewData(null);
    setImportResult(null);
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 gradient-text">
            Data Import & Reconciliatie
          </h2>
          <p className="text-slate-600 mt-1">
            Importeer EPD en bank gegevens, reconcilieer transacties
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              {getIcon(tab.icon)}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'upload' && (
          <div className="space-y-6">
            {!previewData && !importResult && (
              <ImportUpload onPreviewReady={setPreviewData} />
            )}
            
            {previewData && !importResult && (
              <ImportPreview 
                previewData={previewData} 
                onComplete={handlePreviewComplete}
                onBack={() => setPreviewData(null)}
              />
            )}
            
            {importResult && (
              <ImportResult 
                result={importResult}
                onBack={handleBackToUpload}
              />
            )}
          </div>
        )}

        {activeTab === 'reconciliation' && (
          <BankReconciliation onRefresh={onRefresh} />
        )}
      </div>
    </div>
  );
};

export default ImportManager;