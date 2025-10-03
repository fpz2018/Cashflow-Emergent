import React, { useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DataCleanup = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  const handleCleanup = async (type) => {
    if (!window.confirm(`Weet je zeker dat je ${type} wilt verwijderen? Dit kan niet ongedaan gemaakt worden!`)) {
      return;
    }

    try {
      setLoading(true);
      setError('');
      setResult('');

      let endpoint;
      switch(type) {
        case 'alle data':
          endpoint = '/cleanup/all-data';
          break;
        case 'correcties':
          endpoint = '/cleanup/corrections';
          break;
        case 'transacties':
          endpoint = '/cleanup/transactions';
          break;
        case 'bank transacties':
          endpoint = '/cleanup/bank-transactions';
          break;
        default:
          return;
      }

      const response = await axios.delete(`${API}${endpoint}`);
      setResult(response.data.message);
      
    } catch (error) {
      console.error('Cleanup error:', error);
      setError(error.response?.data?.detail || 'Fout bij opschonen data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 gradient-text">
            Data Cleanup
          </h2>
          <p className="text-slate-600 mt-1">
            Verwijder data voor schone tests
          </p>
        </div>
      </div>

      {/* Warning */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-red-600 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 15.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <div>
            <h3 className="text-red-800 font-medium">Waarschuwing</h3>
            <p className="text-red-700 text-sm mt-1">
              Het verwijderen van data kan niet ongedaan worden gemaakt. Gebruik dit alleen voor testing doeleinden.
            </p>
          </div>
        </div>
      </div>

      {/* Feedback Messages */}
      {error && (
        <div className="error-state">
          {error}
        </div>
      )}

      {result && (
        <div className="success-state">
          {result}
        </div>
      )}

      {/* Cleanup Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="modern-card">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-3">
              Selectief Opschonen
            </h3>
            <div className="space-y-3">
              <button
                onClick={() => handleCleanup('correcties')}
                disabled={loading}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Verwijderen...' : 'Alleen Correcties Verwijderen'}
              </button>

              <button
                onClick={() => handleCleanup('transacties')}
                disabled={loading}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Verwijderen...' : 'Alleen Transacties Verwijderen'}
              </button>

              <button
                onClick={() => handleCleanup('bank transacties')}
                disabled={loading}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Verwijderen...' : 'Alleen Bank Transacties Verwijderen'}
              </button>
            </div>
          </div>
        </div>

        <div className="modern-card">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-3">
              Volledig Opschonen
            </h3>
            <p className="text-slate-600 text-sm mb-4">
              Verwijdert alle data uit alle tabellen. Gebruik dit voor een volledige reset.
            </p>
            <button
              onClick={() => handleCleanup('alle data')}
              disabled={loading}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 font-medium"
            >
              {loading ? 'Verwijderen...' : 'ALLE DATA VERWIJDEREN'}
            </button>
          </div>
        </div>
      </div>

      {/* Data Status */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-lg font-semibold text-slate-900">
            Huidige Data Status
          </h3>
        </div>
        <div className="text-sm text-slate-600">
          <p className="mb-2">
            Na het opschonen van data kun je verse data uploaden om de correctie matching te testen.
          </p>
          <ul className="list-disc list-inside space-y-1">
            <li>Upload eerst particuliere facturen via Import & Reconciliatie</li>
            <li>Upload dan zorgverzekeraar declaraties via Import & Reconciliatie</li>
            <li>Test creditfactuur matching via Data Setup → Correcties → Bulk Import</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DataCleanup;