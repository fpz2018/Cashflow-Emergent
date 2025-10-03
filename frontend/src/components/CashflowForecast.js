import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CashflowForecast = () => {
  const [forecastData, setForecastData] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState('chart'); // chart or table

  useEffect(() => {
    fetchForecast();
  }, [selectedPeriod]);

  const fetchForecast = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await axios.get(`${API}/cashflow-forecast?days=${selectedPeriod}`);
      setForecastData(response.data);
    } catch (error) {
      console.error('Error fetching forecast:', error);
      setError('Fout bij ophalen cashflow prognose');
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
    return new Date(dateString).toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit'
    });
  };

  const getBalanceColor = (balance) => {
    if (balance > 10000) return 'text-green-600';
    if (balance > 0) return 'text-yellow-600';
    return 'text-red-600';
  };

  const periods = [
    { value: 30, label: '30 dagen' },
    { value: 60, label: '60 dagen' },
    { value: 90, label: '90 dagen' }
  ];

  if (loading) {
    return (
      <div className="modern-card">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-48 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-200 rounded w-full"></div>
            <div className="h-4 bg-slate-200 rounded w-3/4"></div>
            <div className="h-4 bg-slate-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modern-card">
        <div className="error-state">
          {error}
        </div>
      </div>
    );
  }

  if (!forecastData) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="modern-card">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">
              Cashflow Prognose
            </h3>
            <p className="text-sm text-slate-500">
              Verwachte dagelijkse banksaldo ontwikkeling
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Period Selector */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Periode:</label>
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(Number(e.target.value))}
                className="form-select text-sm"
              >
                {periods.map(period => (
                  <option key={period.value} value={period.value}>
                    {period.label}
                  </option>
                ))}
              </select>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('chart')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  viewMode === 'chart' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Grafiek
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  viewMode === 'table' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Tabel
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="modern-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Huidig Saldo</p>
              <p className="text-xl font-bold text-slate-900">
                {formatCurrency(forecastData.current_balance || 0)}
              </p>
            </div>
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
          </div>
        </div>

        <div className="modern-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Verwachte Inkomsten</p>
              <p className="text-xl font-bold text-green-600">
                {formatCurrency(forecastData.total_expected_income || 0)}
              </p>
            </div>
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
              </svg>
            </div>
          </div>
        </div>

        <div className="modern-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Verwachte Uitgaven</p>
              <p className="text-xl font-bold text-red-600">
                {formatCurrency(Math.abs(forecastData.total_expected_expenses || 0))}
              </p>
            </div>
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
              </svg>
            </div>
          </div>
        </div>

        <div className="modern-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Eindsaldo</p>
              <p className={`text-xl font-bold ${getBalanceColor(forecastData.final_balance || 0)}`}>
                {formatCurrency(forecastData.final_balance || 0)}
              </p>
            </div>
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Chart View */}
      {viewMode === 'chart' && forecastData.forecast_days && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">
              Banksaldo Ontwikkeling
            </h4>
          </div>
          
          <div className="relative">
            {/* Simple line chart visualization */}
            <div className="h-64 flex items-end justify-between border-b border-l border-slate-200 pb-4 pl-4 space-x-1">
              {forecastData.forecast_days.slice(0, 30).map((day, index) => {
                const maxBalance = Math.max(...forecastData.forecast_days.map(d => d.balance));
                const minBalance = Math.min(...forecastData.forecast_days.map(d => d.balance));
                const range = maxBalance - minBalance;
                const height = range > 0 ? ((day.balance - minBalance) / range) * 200 + 20 : 120;
                
                return (
                  <div key={index} className="flex flex-col items-center">
                    <div 
                      className={`w-2 rounded-t transition-all hover:opacity-80 ${
                        day.balance > 0 ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{ height: `${height}px` }}
                      title={`${formatDate(day.date)}: ${formatCurrency(day.balance)}`}
                    />
                    {index % 5 === 0 && (
                      <span className="text-xs text-slate-500 mt-1 rotate-45 origin-left">
                        {formatDate(day.date)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && forecastData.forecast_days && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">
              Gedetailleerde Prognose
            </h4>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Datum
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Inkomsten
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Uitgaven  
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Netto
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Banksaldo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {forecastData.forecast_days.slice(0, 14).map((day, index) => (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                      {formatDate(day.date)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-green-600">
                      {day.income > 0 ? formatCurrency(day.income) : '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-red-600">
                      {day.expenses > 0 ? formatCurrency(Math.abs(day.expenses)) : '-'}
                    </td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm ${
                      (day.income + day.expenses) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(day.income + day.expenses)}
                    </td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm font-medium ${getBalanceColor(day.balance)}`}>
                      {formatCurrency(day.balance)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {day.transactions?.length > 0 ? `${day.transactions.length} transactie(s)` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {forecastData.forecast_days.length > 14 && (
            <div className="px-4 py-3 text-center text-sm text-slate-500 border-t border-slate-200">
              Toont eerste 14 dagen van {forecastData.forecast_days.length} dagen prognose
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CashflowForecast;