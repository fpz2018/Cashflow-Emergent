import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Simple, robust tooltip component
const Tooltip = ({ content, visible, x, y }) => {
  if (!visible || !content) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        left: x + 10,
        top: y - 10,
        backgroundColor: 'white',
        border: '2px solid #64748b',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
        zIndex: 10000,
        maxWidth: '350px',
        minWidth: '250px',
        fontFamily: 'system-ui, sans-serif'
      }}
    >
      {content}
    </div>
  );
};

const Dashboard = ({ onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cashflowData, setCashflowData] = useState(null);
  const [currentBalance, setCurrentBalance] = useState(0);
  const [expandedRow, setExpandedRow] = useState(null);

  // Fetch dagelijkse cashflow forecast
  const fetchCashflowForecast = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Haal 30-dagen forecast op
      const forecastResponse = await axios.get(`${API}/cashflow-forecast?days=30`);
      const forecastData = forecastResponse.data;
      
      // Bereken huidige banksaldo (vandaag)
      const today = new Date();
      const todayStr = today.toISOString().split('T')[0];
      
      // Zoek vandaag in de forecast data
      const todayForecast = forecastData.forecast_days?.find(day => 
        day.date === todayStr
      );
      
      const calculatedBalance = todayForecast ? todayForecast.ending_balance : 0;
      
      setCashflowData(forecastData);
      setCurrentBalance(calculatedBalance);
      
    } catch (error) {
      console.error('Error fetching cashflow forecast:', error);
      setError('Fout bij ophalen cashflow gegevens');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCashflowForecast();
  }, []);

  const toggleRowExpansion = (date) => {
    setExpandedRow(expandedRow === date ? null : date);
  };

  const renderExpandedRow = (day) => {
    if (!day.payments || day.payments.length === 0) {
      return (
        <tr>
          <td colSpan="5" className="px-6 py-4 bg-slate-50">
            <div className="text-center text-slate-500 text-sm">
              Geen transacties voor deze dag
            </div>
          </td>
        </tr>
      );
    }

    const inkomsten = day.payments.filter(p => p.type === 'inkomst');
    const uitgaven = day.payments.filter(p => p.type === 'uitgave');

    return (
      <tr>
        <td colSpan="5" className="px-6 py-4 bg-slate-50 border-l-4 border-blue-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inkomsten */}
            {inkomsten.length > 0 && (
              <div>
                <h4 className="font-semibold text-emerald-700 mb-3 flex items-center">
                  💰 Inkomsten ({inkomsten.length})
                </h4>
                <div className="space-y-2">
                  {inkomsten.map((payment, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-emerald-50 p-3 rounded-lg">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-slate-800">
                          {payment.beschrijving || 'Geen beschrijving'}
                        </div>
                      </div>
                      <div className="text-emerald-700 font-bold">
                        +{formatCurrency(Math.abs(payment.bedrag || 0))}
                      </div>
                    </div>
                  ))}
                  <div className="flex justify-between items-center bg-emerald-100 p-2 rounded font-bold text-emerald-800">
                    <span>Totaal Inkomsten:</span>
                    <span>+{formatCurrency(inkomsten.reduce((sum, p) => sum + Math.abs(p.bedrag || 0), 0))}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Uitgaven */}
            {uitgaven.length > 0 && (
              <div>
                <h4 className="font-semibold text-red-700 mb-3 flex items-center">
                  💳 Uitgaven ({uitgaven.length})
                </h4>
                <div className="space-y-2">
                  {uitgaven.map((payment, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-red-50 p-3 rounded-lg">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-slate-800">
                          {payment.beschrijving || 'Geen beschrijving'}
                        </div>
                      </div>
                      <div className="text-red-700 font-bold">
                        -{formatCurrency(Math.abs(payment.bedrag || 0))}
                      </div>
                    </div>
                  ))}
                  <div className="flex justify-between items-center bg-red-100 p-2 rounded font-bold text-red-800">
                    <span>Totaal Uitgaven:</span>
                    <span>-{formatCurrency(uitgaven.reduce((sum, p) => sum + Math.abs(p.bedrag || 0), 0))}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </td>
      </tr>
    );
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('nl-NL', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner w-8 h-8"></div>
        <span className="ml-3 text-slate-600">Cashflow gegevens laden...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-red-600">
          {error}
          <button 
            onClick={fetchCashflowForecast}
            className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Opnieuw proberen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 gradient-text">
            Cashflow Dashboard
          </h2>
          <p className="text-slate-600 mt-1">
            {formatDate(new Date())}
          </p>
        </div>
        
        <button
          onClick={fetchCashflowForecast}
          className="px-4 py-2 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
        >
          <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Vernieuwen
        </button>
      </div>

      {/* Huidig Banksaldo - Prominent */}
      <div className="modern-card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 shadow-lg">
        <div className="text-center py-6">
          <h3 className="text-lg font-medium text-slate-700 mb-2">💳 Huidig Banksaldo</h3>
          <div className="text-5xl font-bold mb-2">
            <span className={currentBalance >= 0 ? 'text-emerald-600' : 'text-red-600'}>
              {formatCurrency(currentBalance)}
            </span>
          </div>
          <p className="text-slate-600">Per {formatDate(new Date()).split(',')[0]}</p>
        </div>
      </div>

      {/* Quick Stats - Direct onder banksaldo */}
      {cashflowData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="modern-card text-center bg-emerald-50 border-emerald-200">
            <h4 className="text-sm font-medium text-emerald-700 mb-2">📈 Verwachte Inkomsten (30d)</h4>
            <div className="text-2xl font-bold text-emerald-600">
              {formatCurrency(cashflowData.total_expected_income)}
            </div>
          </div>
          
          <div className="modern-card text-center bg-red-50 border-red-200">
            <h4 className="text-sm font-medium text-red-700 mb-2">📉 Verwachte Uitgaven (30d)</h4>
            <div className="text-2xl font-bold text-red-600">
              {formatCurrency(Math.abs(cashflowData.total_expected_expenses))}
            </div>
          </div>
          
          <div className="modern-card text-center bg-slate-50 border-slate-200">
            <h4 className="text-sm font-medium text-slate-700 mb-2">💡 Netto Prognose (30d)</h4>
            <div className={`text-2xl font-bold ${cashflowData.net_expected >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {cashflowData.net_expected >= 0 ? '+' : ''}{formatCurrency(cashflowData.net_expected)}
            </div>
          </div>
        </div>
      )}

      {/* Dagelijkse Cashflow Tabel */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h3 className="text-xl font-semibold text-slate-900">📅 Dagelijkse Cashflow Prognose</h3>
          <p className="text-sm text-slate-500">Komende 14 dagen - per dag overzicht</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Datum
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Inkomsten
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Uitgaven
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Netto
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Banksaldo
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {cashflowData?.forecast_days?.slice(0, 14).map((day, index) => {
                const dayIncome = day.expected_income || 0;
                const dayExpenses = Math.abs(day.expected_expenses || 0);
                const dayNet = dayIncome - dayExpenses;
                const isToday = day.date === new Date().toISOString().split('T')[0];
                
                return (
                  <tr key={day.date} className={isToday ? 'bg-blue-50' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-900">
                        {formatDate(day.date)}
                        {isToday && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Vandaag
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <span 
                        style={{
                          fontWeight: '500',
                          color: '#059669',
                          cursor: 'help',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.backgroundColor = '#ecfdf5';
                          handleMouseEnter(e, 'income', day.payments || []);
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.backgroundColor = 'transparent';
                          handleMouseLeave();
                        }}
                      >
                        {formatCurrency(dayIncome)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <span 
                        style={{
                          fontWeight: '500',
                          color: '#dc2626',
                          cursor: 'help',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.backgroundColor = '#fef2f2';
                          handleMouseEnter(e, 'expense', day.payments || []);
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.backgroundColor = 'transparent';
                          handleMouseLeave();
                        }}
                      >
                        {formatCurrency(dayExpenses)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <span 
                        style={{
                          fontWeight: '600',
                          color: dayNet >= 0 ? '#059669' : '#dc2626',
                          cursor: 'help',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.backgroundColor = '#f8fafc';
                          handleMouseEnter(e, 'net', day.payments || []);
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.backgroundColor = 'transparent';
                          handleMouseLeave();
                        }}
                      >
                        {dayNet >= 0 ? '+' : ''}{formatCurrency(dayNet)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <div className={`px-3 py-1 rounded-lg font-bold text-lg inline-block ${
                        day.ending_balance >= 0 
                          ? 'bg-emerald-100 text-emerald-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {formatCurrency(day.ending_balance)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {!cashflowData?.forecast_days?.length && (
          <div className="text-center py-8 text-slate-500">
            Geen cashflow data beschikbaar
          </div>
        )}
      </div>

      {/* Deze sectie is verplaatst naar boven */}

      {/* Tooltip */}
      <Tooltip 
        content={tooltip.content}
        visible={tooltip.visible}
        x={tooltip.x}
        y={tooltip.y}
      />
    </div>
  );
};

export default Dashboard;