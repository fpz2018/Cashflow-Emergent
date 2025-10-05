import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Tooltip component for showing payment details
const PaymentTooltip = ({ payments, type, visible, position }) => {
  if (!visible || !payments || payments.length === 0) {
    return null;
  }

  let filteredPayments;
  let title;
  
  if (type === 'income') {
    filteredPayments = payments.filter(p => p.type === 'inkomst');
    title = '💰 Inkomsten details:';
  } else if (type === 'expense') {
    filteredPayments = payments.filter(p => p.type === 'uitgave');
    title = '💳 Uitgaven details:';
  } else if (type === 'net') {
    filteredPayments = payments;
    title = '📊 Alle transacties:';
  }

  if (!filteredPayments || filteredPayments.length === 0) {
    return (
      <div 
        className="fixed z-[9999] bg-white border border-slate-400 rounded-lg shadow-xl p-3 max-w-xs"
        style={{ 
          left: Math.min(position.x + 10, window.innerWidth - 300), 
          top: Math.max(position.y - 10, 10),
          pointerEvents: 'none'
        }}
      >
        <div className="text-sm text-slate-500">
          Geen {type === 'income' ? 'inkomsten' : 'uitgaven'} voor deze dag
        </div>
      </div>
    );
  }

  return (
    <div 
      className="fixed z-[9999] bg-white border border-slate-400 rounded-lg shadow-xl p-3 max-w-sm min-w-72"
      style={{ 
        left: Math.min(position.x + 10, window.innerWidth - 350), 
        top: Math.max(position.y - 10, 10),
        maxHeight: '400px',
        overflowY: 'auto',
        pointerEvents: 'none'
      }}
    >
      <div className="text-sm font-semibold mb-2 text-slate-800 border-b pb-1">
        {title}
      </div>
      <div className="space-y-1.5">
        {filteredPayments.map((payment, idx) => (
          <div key={idx} className="flex justify-between items-start gap-3 text-xs bg-slate-50 p-2 rounded">
            <div className="text-slate-700 flex-1 font-medium">
              {payment.beschrijving || 'Geen beschrijving'}
            </div>
            <div className={`font-bold whitespace-nowrap text-sm ${
              payment.type === 'inkomst' ? 'text-emerald-700' : 'text-red-700'
            }`}>
              {payment.type === 'inkomst' ? '+' : '-'}€{Math.abs(payment.bedrag || 0).toLocaleString('nl-NL', { minimumFractionDigits: 2 })}
            </div>
          </div>
        ))}
      </div>
      {type !== 'net' && (
        <div className="mt-3 pt-2 border-t border-slate-300">
          <div className="flex justify-between text-sm font-bold bg-slate-100 p-2 rounded">
            <span className="text-slate-700">Totaal:</span>
            <span className={type === 'income' ? 'text-emerald-700' : 'text-red-700'}>
              €{filteredPayments.reduce((sum, p) => sum + Math.abs(p.bedrag || 0), 0).toLocaleString('nl-NL', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

const Dashboard = ({ onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cashflowData, setCashflowData] = useState(null);
  const [currentBalance, setCurrentBalance] = useState(0);
  const [tooltip, setTooltip] = useState({
    visible: false,
    type: null,
    payments: [],
    position: { x: 0, y: 0 }
  });

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

  const handleMouseEnter = (event, type, payments) => {
    const rect = event.target.getBoundingClientRect();
    setTooltip({
      visible: true,
      type: type,
      payments: payments,
      position: { x: rect.left, y: rect.top }
    });
  };

  const handleMouseLeave = () => {
    setTooltip({
      visible: false,
      type: null,
      payments: [],
      position: { x: 0, y: 0 }
    });
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
                        className="font-medium text-emerald-600 cursor-help hover:bg-emerald-50 px-2 py-1 rounded transition-colors"
                        onMouseEnter={(e) => handleMouseEnter(e, 'income', day.payments || [])}
                        onMouseLeave={handleMouseLeave}
                      >
                        {formatCurrency(dayIncome)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <span 
                        className="font-medium text-red-600 cursor-help hover:bg-red-50 px-2 py-1 rounded transition-colors"
                        onMouseEnter={(e) => handleMouseEnter(e, 'expense', day.payments || [])}
                        onMouseLeave={handleMouseLeave}
                      >
                        {formatCurrency(dayExpenses)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <span 
                        className={`font-semibold cursor-help hover:bg-slate-50 px-2 py-1 rounded transition-colors ${dayNet >= 0 ? 'text-emerald-600' : 'text-red-600'}`}
                        onMouseEnter={(e) => handleMouseEnter(e, 'net', day.payments || [])}
                        onMouseLeave={handleMouseLeave}
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

      {/* Payment Details Tooltip */}
      <PaymentTooltip 
        payments={tooltip.payments}
        type={tooltip.type}
        visible={tooltip.visible}
        position={tooltip.position}
      />
    </div>
  );
};

export default Dashboard;