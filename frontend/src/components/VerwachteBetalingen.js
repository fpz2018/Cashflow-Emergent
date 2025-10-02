import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const VerwachteBetalingen = () => {
  const [verwachteBetalingen, setVerwachteBetalingen] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchVerwachteBetalingen();
  }, []);

  const fetchVerwachteBetalingen = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/verwachte-betalingen`);
      setVerwachteBetalingen(response.data);
    } catch (error) {
      console.error('Error fetching verwachte betalingen:', error);
      setError('Fout bij ophalen verwachte betalingen');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const diffDays = Math.ceil((date - today) / (1000 * 60 * 60 * 24));
    
    const formattedDate = date.toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit'
    });

    if (diffDays < 0) {
      return `${formattedDate} (${Math.abs(diffDays)}d geleden)`;
    } else if (diffDays === 0) {
      return `${formattedDate} (vandaag)`;
    } else if (diffDays === 1) {
      return `${formattedDate} (morgen)`;
    } else {
      return `${formattedDate} (${diffDays}d)`;
    }
  };

  const getStatusColor = (status, verwachte_datum) => {
    const today = new Date();
    const datum = new Date(verwachte_datum);
    
    if (status === 'overdue' || datum < today) {
      return 'text-red-600 bg-red-50';
    } else if (datum <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)) {
      return 'text-orange-600 bg-orange-50';
    } else {
      return 'text-green-600 bg-green-50';
    }
  };

  const getTypeIcon = (type) => {
    if (type === 'declaratie') {
      return (
        <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
        </svg>
      );
    } else {
      return (
        <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      );
    }
  };

  if (loading) {
    return (
      <div className="modern-card">
        <div className="flex items-center justify-center py-8">
          <div className="spinner w-6 h-6"></div>
          <span className="ml-3 text-slate-600">Verwachte betalingen laden...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="modern-card" data-testid="verwachte-betalingen">
      <div className="modern-card-header">
        <h3 className="text-lg font-semibold text-slate-900">Verwachte Betalingen</h3>
        <button
          onClick={fetchVerwachteBetalingen}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          Vernieuwen
        </button>
      </div>

      {error && (
        <div className="error-state mb-4">
          {error}
        </div>
      )}

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {verwachteBetalingen.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a4 4 0 118 0v4m-4 8a2 2 0 100-4 2 2 0 000 4z" />
            </svg>
            Geen verwachte betalingen
          </div>
        ) : (
          verwachteBetalingen.map((betaling, index) => (
            <div
              key={betaling.id}
              className={`p-4 rounded-lg border transition-all card-hover ${getStatusColor(betaling.status, betaling.verwachte_datum)}`}
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getTypeIcon(betaling.type)}
                  
                  <div>
                    <h4 className="font-medium text-slate-900">
                      {betaling.beschrijving}
                    </h4>
                    <div className="flex items-center gap-4 text-sm text-slate-600 mt-1">
                      <span>{formatDate(betaling.verwachte_datum)}</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        betaling.type === 'declaratie' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {betaling.type === 'declaratie' ? 'Inkomst' : 'Uitgave'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className={`text-lg font-bold ${
                    betaling.bedrag >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {betaling.bedrag >= 0 ? '+' : ''}{formatCurrency(betaling.bedrag)}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {verwachteBetalingen.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-200">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-lg font-bold text-green-600">
                {formatCurrency(
                  verwachteBetalingen
                    .filter(b => b.bedrag > 0)
                    .reduce((sum, b) => sum + b.bedrag, 0)
                )}
              </div>
              <div className="text-xs text-slate-600">Verwachte Inkomsten</div>
            </div>
            
            <div>
              <div className="text-lg font-bold text-red-600">
                {formatCurrency(
                  Math.abs(verwachteBetalingen
                    .filter(b => b.bedrag < 0)
                    .reduce((sum, b) => sum + b.bedrag, 0))
                )}
              </div>
              <div className="text-xs text-slate-600">Verwachte Uitgaven</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VerwachteBetalingen;