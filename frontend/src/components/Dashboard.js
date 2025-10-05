import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Uitklapbare rijen - veel betrouwbaarder dan tooltips

const Dashboard = ({ onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cashflowData, setCashflowData] = useState(null);
  const [currentBalance, setCurrentBalance] = useState(0);
  const [expandedRow, setExpandedRow] = useState(null);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [editForm, setEditForm] = useState({
    beschrijving: '',
    bedrag: '',
    type: 'inkomst',
    datum: ''
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

  const toggleRowExpansion = (date) => {
    setExpandedRow(expandedRow === date ? null : date);
  };

  const handleEditTransaction = (payment, dayDate) => {
    setEditingTransaction({ ...payment, dayDate });
    setEditForm({
      beschrijving: payment.beschrijving || '',
      bedrag: Math.abs(payment.bedrag || 0).toString(),
      type: payment.type,
      datum: dayDate || new Date().toISOString().split('T')[0]
    });
  };

  const handleSaveTransaction = async () => {
    try {
      setLoading(true);
      setError('');

      // Determine the correct API endpoint based on transaction type and content
      let apiEndpoint;
      let updateData = {
        description: editForm.beschrijving,
        amount: editForm.type === 'uitgave' ? -Math.abs(parseFloat(editForm.bedrag)) : Math.abs(parseFloat(editForm.bedrag))
      };

      // Check if this is a declaration (has invoice number) or creditor payment
      if (editingTransaction.beschrijving?.includes('Declaratie')) {
        // This is likely a transaction from the transactions collection
        apiEndpoint = `${API}/transactions/${editingTransaction.id || 'unknown'}`;
        updateData = {
          ...updateData,
          type: editForm.type === 'inkomst' ? 'income' : 'expense'
        };
      } else if (editingTransaction.beschrijving?.includes('Betaling')) {
        // This is likely a creditor payment - we need to update the creditor
        const crediteurNaam = editingTransaction.beschrijving.replace('Betaling ', '');
        apiEndpoint = `${API}/crediteuren`;
        
        // Find and update the specific creditor
        const crediteurenResponse = await axios.get(`${API}/crediteuren`);
        const crediteuren = crediteurenResponse.data;
        const targetCrediteur = crediteuren.find(c => c.crediteur === crediteurNaam);
        
        if (targetCrediteur) {
          updateData = {
            ...targetCrediteur,
            crediteur: editForm.beschrijving.replace('Betaling ', ''),
            bedrag: Math.abs(parseFloat(editForm.bedrag))
          };
          apiEndpoint = `${API}/crediteuren/${targetCrediteur.id}`;
        }
      } else {
        // Generic transaction update
        apiEndpoint = `${API}/transactions/${editingTransaction.id || 'unknown'}`;
      }

      await axios.put(apiEndpoint, updateData);
      
      // Refresh data
      await fetchCashflowForecast();
      
      // Close edit modal
      setEditingTransaction(null);
      setEditForm({ beschrijving: '', bedrag: '', type: 'inkomst' });
      
    } catch (error) {
      console.error('Error updating transaction:', error);
      setError(`Fout bij wijzigen transactie: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTransaction = async () => {
    if (!window.confirm('Weet u zeker dat u deze transactie wilt verwijderen?')) return;
    
    try {
      setLoading(true);
      setError('');

      // Similar logic for deletion
      let apiEndpoint;
      
      if (editingTransaction.beschrijving?.includes('Declaratie')) {
        apiEndpoint = `${API}/transactions/${editingTransaction.id}`;
      } else if (editingTransaction.beschrijving?.includes('Betaling')) {
        const crediteurNaam = editingTransaction.beschrijving.replace('Betaling ', '');
        const crediteurenResponse = await axios.get(`${API}/crediteuren`);
        const crediteuren = crediteurenResponse.data;
        const targetCrediteur = crediteuren.find(c => c.crediteur === crediteurNaam);
        
        if (targetCrediteur) {
          apiEndpoint = `${API}/crediteuren/${targetCrediteur.id}`;
        }
      } else {
        apiEndpoint = `${API}/transactions/${editingTransaction.id}`;
      }

      await axios.delete(apiEndpoint);
      
      // Refresh data
      await fetchCashflowForecast();
      
      // Close edit modal
      setEditingTransaction(null);
      setEditForm({ beschrijving: '', bedrag: '', type: 'inkomst' });
      
    } catch (error) {
      console.error('Error deleting transaction:', error);
      setError(`Fout bij verwijderen transactie: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
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
                    <div key={idx} className="flex justify-between items-center bg-emerald-50 p-3 rounded-lg hover:bg-emerald-100 transition-colors">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-slate-800">
                          {payment.beschrijving || 'Geen beschrijving'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-emerald-700 font-bold">
                          +{formatCurrency(Math.abs(payment.bedrag || 0))}
                        </div>
                        <button
                          onClick={() => handleEditTransaction(payment, day.date)}
                          className="p-1 text-slate-500 hover:text-emerald-700 hover:bg-white rounded transition-colors"
                          title="Bewerk transactie"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
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
                    <div key={idx} className="flex justify-between items-center bg-red-50 p-3 rounded-lg hover:bg-red-100 transition-colors">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-slate-800">
                          {payment.beschrijving || 'Geen beschrijving'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-red-700 font-bold">
                          -{formatCurrency(Math.abs(payment.bedrag || 0))}
                        </div>
                        <button
                          onClick={() => handleEditTransaction(payment, day.date)}
                          className="p-1 text-slate-500 hover:text-red-700 hover:bg-white rounded transition-colors"
                          title="Bewerk transactie"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
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
                const isExpanded = expandedRow === day.date;
                const hasTransactions = day.payments && day.payments.length > 0;
                
                return (
                  <React.Fragment key={day.date}>
                    <tr 
                      className={`${isToday ? 'bg-blue-50' : ''} ${hasTransactions ? 'cursor-pointer hover:bg-slate-50' : ''} transition-colors`}
                      onClick={() => hasTransactions && toggleRowExpansion(day.date)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {hasTransactions && (
                            <button className="mr-2 text-slate-500 hover:text-slate-700">
                              <svg 
                                className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} 
                                fill="none" 
                                stroke="currentColor" 
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </button>
                          )}
                          <div className="text-sm font-medium text-slate-900">
                            {formatDate(day.date)}
                            {isToday && (
                              <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                Vandaag
                              </span>
                            )}
                            {hasTransactions && (
                              <span className="ml-2 text-xs text-slate-500">
                                ({day.payments.length} transacties)
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <span className="font-medium text-emerald-600">
                          {formatCurrency(dayIncome)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <span className="font-medium text-red-600">
                          {formatCurrency(dayExpenses)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <span className={`font-semibold ${dayNet >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
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
                    {isExpanded && renderExpandedRow(day)}
                  </React.Fragment>
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

      {/* Edit Transaction Modal */}
      {editingTransaction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">
                  Transactie Bewerken
                </h3>
                <button
                  onClick={() => setEditingTransaction(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="mb-4">
                <div className="bg-slate-50 p-3 rounded-lg mb-4">
                  <div className="text-sm text-slate-600">Datum:</div>
                  <div className="font-medium">
                    {editingTransaction.dayDate ? formatDate(editingTransaction.dayDate) : 'Onbekend'}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Type Transactie
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setEditForm({...editForm, type: 'inkomst'})}
                      className={`p-3 border rounded-lg text-center transition-all ${
                        editForm.type === 'inkomst'
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      💰 Inkomst
                    </button>
                    <button
                      onClick={() => setEditForm({...editForm, type: 'uitgave'})}
                      className={`p-3 border rounded-lg text-center transition-all ${
                        editForm.type === 'uitgave'
                          ? 'border-red-500 bg-red-50 text-red-700'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      💳 Uitgave
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Beschrijving
                  </label>
                  <input
                    type="text"
                    value={editForm.beschrijving}
                    onChange={(e) => setEditForm({...editForm, beschrijving: e.target.value})}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Transactie beschrijving"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Bedrag (€)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editForm.bedrag}
                    onChange={(e) => setEditForm({...editForm, bedrag: e.target.value})}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div className="flex justify-between gap-3 mt-6">
                <button
                  onClick={handleDeleteTransaction}
                  className="px-4 py-2 text-red-600 hover:text-red-700 border border-red-300 rounded-lg hover:bg-red-50 transition-all"
                  disabled={loading}
                >
                  🗑️ Verwijderen
                </button>
                
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingTransaction(null)}
                    className="px-4 py-2 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
                    disabled={loading}
                  >
                    Annuleren
                  </button>
                  <button
                    onClick={handleSaveTransaction}
                    disabled={!editForm.beschrijving.trim() || !editForm.bedrag.trim() || loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all"
                  >
                    {loading ? 'Opslaan...' : 'Opslaan'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Uitklapbare rijen geven betrouwbaar inzicht in alle transacties */}
    </div>
  );
};

export default Dashboard;