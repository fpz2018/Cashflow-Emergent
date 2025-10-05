import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const BankReconciliation = ({ onRefresh }) => {
  const [bankTransactions, setBankTransactions] = useState([]);
  const [cashflowTransactions, setCashflowTransactions] = useState([]);
  const [selectedBankTransaction, setSelectedBankTransaction] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  const [classificationForm, setClassificationForm] = useState({
    type: 'vast', // 'vast' or 'variabel'
    categoryName: ''
  });

  useEffect(() => {
    fetchUnmatchedTransactions();
  }, []);

  const fetchUnmatchedTransactions = async () => {
    try {
      setLoading(true);
      setError('');
      console.log('Fetching unmatched transactions from:', `${API}/bank-reconciliation/unmatched`);
      
      // Fetch unmatched bank transactions
      const bankResponse = await axios.get(`${API}/bank-reconciliation/unmatched`);
      console.log('Bank transactions received:', bankResponse.data?.length);
      setBankTransactions(bankResponse.data);

      // Fetch unreconciled cashflow transactions
      const cashflowResponse = await axios.get(`${API}/transactions?reconciled=false`);
      console.log('Cashflow transactions received:', cashflowResponse.data?.length);
      setCashflowTransactions(cashflowResponse.data);

    } catch (error) {
      console.error('Error fetching transactions:', error);
      setError(`Fout bij ophalen transacties: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchSuggestions = async (bankTransactionId) => {
    try {
      const response = await axios.get(`${API}/bank-reconciliation/suggestions/${bankTransactionId}`);
      setSuggestions(response.data);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      setSuggestions([]);
    }
  };

  const handleSelectBankTransaction = (transaction) => {
    setSelectedBankTransaction(transaction);
    fetchSuggestions(transaction.id);
  };

  const handleMatch = async (bankTransactionId, cashflowTransactionId) => {
    try {
      console.log('Matching:', { bankTransactionId, cashflowTransactionId });
      
      const response = await axios.post(
        `${API}/bank-reconciliation/match`,
        null,
        {
          params: {
            bank_transaction_id: bankTransactionId,
            transaction_id: cashflowTransactionId
          }
        }
      );
      
      console.log('Match response:', response.data);
      setSuggestions([]);
      setSelectedBankTransaction(null);
      await fetchUnmatchedTransactions();
      onRefresh && onRefresh();
    } catch (error) {
      console.error('Error matching transactions:', error);
      setError(`Fout bij koppelen transacties: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleClassifyTransaction = async (bankTransactionId, classificationType, categoryName) => {
    try {
      setLoading(true);
      setError('');
      
      const response = await axios.post(
        `${API}/bank-reconciliation/classify/${bankTransactionId}`,
        null,
        {
          params: {
            classification_type: classificationType,
            category_name: categoryName
          }
        }
      );
      
      console.log('Classification response:', response.data);
      
      // Reset state and refresh data
      setShowClassificationModal(false);
      setSelectedBankTransaction(null);
      setSuggestions([]);
      setClassificationForm({ type: 'vast', categoryName: '' });
      
      await fetchUnmatchedTransactions();
      onRefresh && onRefresh();
      
    } catch (error) {
      console.error('Error classifying transaction:', error);
      setError(`Fout bij classificeren: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenClassification = () => {
    if (selectedBankTransaction && selectedBankTransaction.amount < 0) {
      setShowClassificationModal(true);
    }
  };

  const handleMatchCrediteur = async (bankTransactionId, crediteurId) => {
    try {
      await axios.post(`${API}/bank-reconciliation/match-crediteur`, null, {
        params: {
          bank_transaction_id: bankTransactionId,
          crediteur_id: crediteurId
        }
      });

      // Refresh data
      await fetchUnmatchedTransactions();
      setSelectedBankTransaction(null);
      setSuggestions([]);
      
      onRefresh && onRefresh();

    } catch (error) {
      console.error('Error matching with crediteur:', error);
      setError('Fout bij koppelen aan crediteur');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('nl-NL');
  };

  const getMatchScore = (bankAmount, cashflowAmount, bankDate, cashflowDate) => {
    const amountMatch = bankAmount === cashflowAmount ? 50 : 0;
    const dateMatch = bankDate === cashflowDate ? 30 : 
                     Math.abs(new Date(bankDate) - new Date(cashflowDate)) <= 7 * 24 * 60 * 60 * 1000 ? 15 : 0;
    return amountMatch + dateMatch;
  };

  if (loading && bankTransactions.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner w-8 h-8"></div>
        <span className="ml-3 text-slate-600">Bank gegevens laden...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Bank Reconciliatie</h3>
          <p className="text-slate-600">
            Koppel bank transacties aan cashflow transacties en crediteuren
          </p>
        </div>
        
        <button
          onClick={fetchUnmatchedTransactions}
          className="px-4 py-2 text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all btn-animation"
          data-testid="refresh-reconciliation-button"
        >
          <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Vernieuwen
        </button>
      </div>

      {error && (
        <div className="error-state" data-testid="reconciliation-error">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bank Transactions */}
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">
              Onbekende Bank Transacties
            </h4>
            <span className="text-sm text-slate-500">
              {bankTransactions.length} transacties
            </span>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {bankTransactions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Geen onbekende bank transacties
              </div>
            ) : (
              bankTransactions.map((transaction) => (
                <div
                  key={transaction.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedBankTransaction?.id === transaction.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                  onClick={() => handleSelectBankTransaction(transaction)}
                  data-testid={`bank-transaction-${transaction.id}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className={`font-medium ${transaction.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatCurrency(transaction.amount)}
                    </div>
                    <div className="text-sm text-slate-500">
                      {formatDate(transaction.date)}
                    </div>
                  </div>
                  
                  <div className="text-sm text-slate-600 mb-1">
                    <strong>Tegenpartij:</strong> {transaction.counterparty || 'Onbekend'}
                  </div>
                  
                  <div className="text-sm text-slate-600 mb-2 truncate">
                    <strong>Omschrijving:</strong> {transaction.description || 'Geen omschrijving'}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      transaction.amount < 0 
                        ? 'bg-red-100 text-red-700' 
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {transaction.amount < 0 ? 'Uitgaand' : 'Inkomend'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Matching Interface */}
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">
              Mogelijke Matches
            </h4>
            {selectedBankTransaction && (
              <div className="text-sm text-slate-500">
                Voor {formatCurrency(selectedBankTransaction.amount)} 
                <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
                  selectedBankTransaction.amount < 0 
                    ? 'bg-red-100 text-red-700' 
                    : 'bg-green-100 text-green-700'
                }`}>
                  {selectedBankTransaction.amount < 0 ? 'Uitgaand' : 'Inkomend'}
                </span>
                <span className="ml-2">- Transacties & Crediteuren</span>
              </div>
            )}
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {!selectedBankTransaction ? (
              <div className="text-center py-8 text-slate-500">
                <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Selecteer een bank transactie om matches te zien
              </div>
            ) : suggestions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <svg className="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div className="mb-4">Geen mogelijke matches gevonden</div>
                
                {/* Classification option for outgoing transactions */}
                {selectedBankTransaction && selectedBankTransaction.amount < 0 && (
                  <div className="space-y-3">
                    <p className="text-sm text-slate-600">
                      Deze uitgaande transactie kan worden geclassificeerd als vaste of variabele kosten
                    </p>
                    <button
                      onClick={handleOpenClassification}
                      className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      Classificeer als Kosten
                    </button>
                  </div>
                )}
              </div>
            ) : (
              suggestions.map((item) => {
                // Calculate match score differently for crediteur vs transaction
                const matchScore = item.match_type === 'crediteur' 
                  ? item.match_score 
                  : getMatchScore(
                      selectedBankTransaction.amount,
                      item.amount,
                      selectedBankTransaction.date,
                      item.date
                    );

                const isTransaction = item.match_type === 'transaction';
                const isCrediteur = item.match_type === 'crediteur';

                return (
                  <div
                    key={item.id}
                    className="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-all"
                    data-testid={`suggestion-${item.id}`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <div className="font-medium text-slate-900">
                          {formatCurrency(item.amount)}
                        </div>
                        {isCrediteur && (
                          <span className="px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-700 font-medium">
                            Crediteur
                          </span>
                        )}
                        {isTransaction && (
                          <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700 font-medium">
                            Transactie
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          matchScore >= 80 ? 'bg-green-100 text-green-700' :
                          matchScore >= 50 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {Math.round(matchScore)}% match
                        </span>
                        {isTransaction && (
                          <span className="text-sm text-slate-500">
                            {formatDate(item.date)}
                          </span>
                        )}
                        {isCrediteur && item.crediteur_dag && (
                          <span className="text-sm text-slate-500">
                            {item.crediteur_dag}e van de maand
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-sm text-slate-600 mb-2">
                      <strong>Beschrijving:</strong> {item.description}
                    </div>
                    
                    {item.match_reason && (
                      <div className="text-sm text-slate-600 mb-2">
                        <strong>Match reden:</strong> {item.match_reason}
                      </div>
                    )}
                    
                    {item.patient_name && isTransaction && (
                      <div className="text-sm text-slate-600 mb-2">
                        <strong>Patiënt:</strong> {item.patient_name}
                      </div>
                    )}
                    
                    <div className="flex justify-between items-center mt-3">
                      <span className={`category-badge category-${item.category}`}>
                        {item.category.toUpperCase()}
                      </span>
                      
                      <button
                        onClick={() => {
                          if (isCrediteur) {
                            handleMatchCrediteur(selectedBankTransaction.id, item.id);
                          } else {
                            handleMatch(selectedBankTransaction.id, item.id);
                          }
                        }}
                        className={`px-3 py-1 text-white text-sm rounded-lg transition-colors btn-animation ${
                          isCrediteur 
                            ? 'bg-purple-600 hover:bg-purple-700' 
                            : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                        data-testid={`match-button-${item.id}`}
                      >
                        {isCrediteur ? 'Koppel Crediteur' : 'Koppelen'}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Unreconciled Cashflow Transactions */}
      <div className="modern-card">
        <div className="modern-card-header">
          <h4 className="text-lg font-semibold text-slate-900">
            Onbehandelde Cashflow Transacties
          </h4>
          <span className="text-sm text-slate-500">
            {cashflowTransactions.filter(t => !t.reconciled).length} transacties
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Datum
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Bedrag
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Beschrijving
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Categorie
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {cashflowTransactions.filter(t => !t.reconciled).map((transaction) => (
                <tr key={transaction.id}>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                    {formatDate(transaction.date)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                    {formatCurrency(transaction.amount)}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-900 max-w-xs truncate">
                    {transaction.description}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`category-badge category-${transaction.category}`}>
                      {transaction.category.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800">
                      Onbehandeld
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {cashflowTransactions.filter(t => !t.reconciled).length === 0 && (
            <div className="text-center py-8 text-slate-500">
              Alle cashflow transacties zijn behandeld
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BankReconciliation;