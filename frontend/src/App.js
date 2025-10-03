import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';
import "./App.css";

// Components
import Dashboard from './components/Dashboard';
import TransactionForm from './components/TransactionForm';
import TransactionList from './components/TransactionList';
import ImportManager from './components/ImportManager';
import DataSetup from './components/DataSetup';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [transactions, setTransactions] = useState([]);
  const [cashflowSummary, setCashflowSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState('dashboard');

  // Fetch cashflow summary
  const fetchCashflowSummary = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/cashflow/summary`);
      setCashflowSummary(response.data);
    } catch (error) {
      console.error('Error fetching cashflow summary:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch transactions
  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/transactions`);
      setTransactions(response.data);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  // Create transaction
  const createTransaction = async (transactionData) => {
    try {
      const response = await axios.post(`${API}/transactions`, transactionData);
      setTransactions(prev => [response.data, ...prev]);
      fetchCashflowSummary(); // Refresh summary
      return response.data;
    } catch (error) {
      console.error('Error creating transaction:', error);
      throw error;
    }
  };

  // Update transaction
  const updateTransaction = async (transactionId, updateData) => {
    try {
      const response = await axios.put(`${API}/transactions/${transactionId}`, updateData);
      setTransactions(prev => 
        prev.map(t => t.id === transactionId ? response.data : t)
      );
      fetchCashflowSummary(); // Refresh summary
      return response.data;
    } catch (error) {
      console.error('Error updating transaction:', error);
      throw error;
    }
  };

  // Delete transaction  
  const deleteTransaction = async (transactionId) => {
    try {
      await axios.delete(`${API}/transactions/${transactionId}`);
      setTransactions(prev => prev.filter(t => t.id !== transactionId));
      fetchCashflowSummary(); // Refresh summary
    } catch (error) {
      console.error('Error deleting transaction:', error);
      throw error;
    }
  };

  useEffect(() => {
    fetchCashflowSummary();
    fetchTransactions();
  }, []);

  return (
    <div className="App">
      <BrowserRouter>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
          {/* Header */}
          <header className="bg-white shadow-sm border-b border-slate-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-slate-900">Fysiotherapie Cashflow</h1>
                    <p className="text-sm text-slate-600">Dagelijkse cashflow monitoring</p>
                  </div>
                </div>
                
                <nav className="flex items-center space-x-6">
                  <button 
                    className={`font-medium transition-colors ${
                      activeView === 'dashboard' ? 'text-blue-600' : 'text-slate-600 hover:text-slate-900'
                    }`}
                    onClick={() => {
                      setActiveView('dashboard');
                      fetchCashflowSummary();
                    }}
                    data-testid="nav-dashboard"
                  >
                    Dashboard
                  </button>
                  <button 
                    className={`font-medium transition-colors ${
                      activeView === 'setup' ? 'text-blue-600' : 'text-slate-600 hover:text-slate-900'
                    }`}
                    onClick={() => setActiveView('setup')}
                    data-testid="nav-setup"
                  >
                    Data Setup
                  </button>
                  <button 
                    className={`font-medium transition-colors ${
                      activeView === 'import' ? 'text-blue-600' : 'text-slate-600 hover:text-slate-900'
                    }`}
                    onClick={() => setActiveView('import')}
                    data-testid="nav-import"
                  >
                    Import & Reconciliatie
                  </button>
                  <button className="text-slate-600 hover:text-slate-900 font-medium transition-colors">
                    Rapporten
                  </button>
                </nav>
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route 
                path="/" 
                element={
                  <>
                    {activeView === 'dashboard' && (
                      <Dashboard 
                        cashflowSummary={cashflowSummary}
                        transactions={transactions}
                        loading={loading}
                        onCreateTransaction={createTransaction}
                        onUpdateTransaction={updateTransaction}
                        onDeleteTransaction={deleteTransaction}
                        onRefresh={fetchCashflowSummary}
                      />
                    )}
                    
                    {activeView === 'setup' && (
                      <DataSetup />
                    )}
                    
                    {activeView === 'import' && (
                      <ImportManager 
                        onRefresh={() => {
                          fetchCashflowSummary();
                          fetchTransactions();
                        }}
                      />
                    )}
                  </>
                } 
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;