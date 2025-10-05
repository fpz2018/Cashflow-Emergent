import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const KostenOverzicht = () => {
  const [vasteKosten, setVasteKosten] = useState([]);
  const [variabeleKosten, setVariabeleKosten] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('vast');

  useEffect(() => {
    fetchKostenData();
  }, []);

  const fetchKostenData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const [vasteResponse, variabeleResponse] = await Promise.all([
        axios.get(`${API}/vaste-kosten`),
        axios.get(`${API}/variabele-kosten`)
      ]);
      
      setVasteKosten(vasteResponse.data);
      setVariabeleKosten(variabeleResponse.data);
      
    } catch (error) {
      console.error('Error fetching kosten data:', error);
      setError('Fout bij ophalen kosten overzicht');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('nl-NL');
  };

  const totalVasteKosten = vasteKosten.reduce((sum, cat) => sum + cat.total_amount, 0);
  const totalVariabeleKosten = variabeleKosten.reduce((sum, cat) => sum + cat.total_amount, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner w-8 h-8"></div>
        <span className="ml-3 text-slate-600">Kosten overzicht laden...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">💰 Kosten Overzicht</h3>
          <p className="text-slate-600">
            Geclassificeerde vaste en variabele kosten uit bank reconciliatie
          </p>
        </div>
        
        <button
          onClick={fetchKostenData}
          className="px-4 py-2 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
        >
          <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Vernieuwen
        </button>
      </div>

      {error && (
        <div className="error-state">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="modern-card bg-red-50 border-red-200">
          <div className="text-center">
            <h4 className="text-sm font-medium text-red-700 mb-2">🏠 Totaal Vaste Kosten</h4>
            <div className="text-2xl font-bold text-red-600">
              {formatCurrency(totalVasteKosten)}
            </div>
            <div className="text-sm text-red-600">
              {vasteKosten.length} categorieën
            </div>
          </div>
        </div>
        
        <div className="modern-card bg-orange-50 border-orange-200">
          <div className="text-center">
            <h4 className="text-sm font-medium text-orange-700 mb-2">📊 Totaal Variabele Kosten</h4>
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(totalVariabeleKosten)}
            </div>
            <div className="text-sm text-orange-600">
              {variabeleKosten.length} categorieën
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('vast')}
            className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all ${
              activeTab === 'vast'
                ? 'border-red-500 text-red-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            🏠 Vaste Kosten
          </button>
          <button
            onClick={() => setActiveTab('variabel')}
            className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all ${
              activeTab === 'variabel'
                ? 'border-orange-500 text-orange-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            📊 Variabele Kosten
          </button>
        </nav>
      </div>

      {/* Kosten Categories */}
      <div className="space-y-4">
        {activeTab === 'vast' && (
          <div>
            {vasteKosten.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 009.586 13H7" />
                </svg>
                Nog geen vaste kosten geclassificeerd
                <p className="text-sm mt-2">
                  Classificeer banktransacties in de reconciliatie om vaste kosten te zien
                </p>
              </div>
            ) : (
              vasteKosten.map((category) => (
                <div key={category.category_name} className="modern-card">
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-lg font-semibold text-slate-900">
                      {category.category_name}
                    </h4>
                    <div className="text-right">
                      <div className="text-xl font-bold text-red-600">
                        {formatCurrency(category.total_amount)}
                      </div>
                      <div className="text-sm text-slate-500">
                        {category.transaction_count} transacties
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    {category.transactions.map((transaction) => (
                      <div key={transaction.id} className="flex justify-between items-center py-2 px-3 bg-slate-50 rounded">
                        <div>
                          <div className="text-sm font-medium text-slate-900">
                            {transaction.description}
                          </div>
                          <div className="text-xs text-slate-500">
                            {formatDate(transaction.date)} • {transaction.counterparty}
                          </div>
                        </div>
                        <div className="text-sm font-medium text-red-600">
                          {formatCurrency(transaction.amount)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'variabel' && (
          <div>
            {variabeleKosten.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Nog geen variabele kosten geclassificeerd
                <p className="text-sm mt-2">
                  Classificeer banktransacties in de reconciliatie om variabele kosten te zien
                </p>
              </div>
            ) : (
              variabeleKosten.map((category) => (
                <div key={category.category_name} className="modern-card">
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-lg font-semibold text-slate-900">
                      {category.category_name}
                    </h4>
                    <div className="text-right">
                      <div className="text-xl font-bold text-orange-600">
                        {formatCurrency(category.total_amount)}
                      </div>
                      <div className="text-sm text-slate-500">
                        {category.transaction_count} transacties
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    {category.transactions.map((transaction) => (
                      <div key={transaction.id} className="flex justify-between items-center py-2 px-3 bg-slate-50 rounded">
                        <div>
                          <div className="text-sm font-medium text-slate-900">
                            {transaction.description}
                          </div>
                          <div className="text-xs text-slate-500">
                            {formatDate(transaction.date)} • {transaction.counterparty}
                          </div>
                        </div>
                        <div className="text-sm font-medium text-orange-600">
                          {formatCurrency(transaction.amount)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default KostenOverzicht;