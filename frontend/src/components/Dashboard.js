import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cashflowData, setCashflowData] = useState(null);
  const [currentBalance, setCurrentBalance] = useState(0);

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
    <div className="space-y-8 fade-in">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 gradient-text">
            Dashboard
          </h2>
          <p className="text-slate-600 mt-1">
            {cashflowSummary?.today?.date ? formatDate(cashflowSummary.today.date) : 'Vandaag'}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            className="px-4 py-2 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all btn-animation"
            data-testid="refresh-button"
          >
            <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Vernieuwen
          </button>
          
          <button
            onClick={() => setShowTransactionForm(true)}
            className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 font-medium shadow-md hover:shadow-lg transition-all btn-animation"
            data-testid="add-transaction-button"
          >
            <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nieuwe Transactie
          </button>
        </div>
      </div>

      {/* Cashflow Cards */}
      <CashflowCards 
        cashflowSummary={cashflowSummary} 
        formatCurrency={formatCurrency}
      />

      {/* Quick Stats */}
      {cashflowSummary?.today && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h3 className="text-lg font-semibold text-slate-900">Vandaag Overzicht</h3>
            <span className="text-sm text-slate-500">
              {cashflowSummary.today.transactions_count} transacties
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Income Categories */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Inkomsten per Categorie</h4>
              <div className="space-y-2">
                {Object.entries(cashflowSummary.today.income_by_category || {}).map(([category, amount]) => (
                  <div key={category} className="flex justify-between items-center">
                    <span className={`category-badge category-${category}`}>
                      {category.replace('_', ' ').toUpperCase()}
                    </span>
                    <span className="font-medium text-emerald-600">
                      {formatCurrency(amount)}
                    </span>
                  </div>
                ))}
                {Object.keys(cashflowSummary.today.income_by_category || {}).length === 0 && (
                  <p className="text-slate-500 text-sm italic">Geen inkomsten vandaag</p>
                )}
              </div>
            </div>

            {/* Expense Categories */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Uitgaven per Categorie</h4>
              <div className="space-y-2">
                {Object.entries(cashflowSummary.today.expense_by_category || {}).map(([category, amount]) => (
                  <div key={category} className="flex justify-between items-center">
                    <span className="category-badge category-expense">
                      {category.replace('_', ' ').toUpperCase()}
                    </span>
                    <span className="font-medium text-red-600">
                      -{formatCurrency(amount)}
                    </span>
                  </div>
                ))}
                {Object.keys(cashflowSummary.today.expense_by_category || {}).length === 0 && (
                  <p className="text-slate-500 text-sm italic">Geen uitgaven vandaag</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions */}
        <div className="modern-card">
          <div className="modern-card-header">
            <h3 className="text-lg font-semibold text-slate-900">Recente Transacties</h3>
            <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              Alle transacties bekijken
            </button>
          </div>
          
          <TransactionList
            transactions={transactions.slice(0, 5)}
            onEdit={handleEditTransaction}
            onDelete={onDeleteTransaction}
            formatCurrency={formatCurrency}
          />
        </div>

        {/* Verwachte Betalingen */}
        <VerwachteBetalingen />
      </div>

      {/* Cashflow Forecast */}
      <CashflowForecast />

      {/* Transaction Form Modal */}
      {showTransactionForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <TransactionForm
              transaction={editingTransaction}
              onSubmit={editingTransaction ? 
                (data) => handleUpdateTransaction(editingTransaction.id, data) : 
                handleCreateTransaction
              }
              onCancel={() => {
                setShowTransactionForm(false);
                setEditingTransaction(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;