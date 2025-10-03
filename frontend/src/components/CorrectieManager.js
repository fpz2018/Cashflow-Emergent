import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CorrectieManager = () => {
  const [activeTab, setActiveTab] = useState('create');
  const [correcties, setCorrecties] = useState([]);
  const [unmatchedCorrecties, setUnmatchedCorrecties] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedCorrectie, setSelectedCorrectie] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Bulk import state
  const [bulkSubTab, setBulkSubTab] = useState('creditfactuur');
  const [bulkData, setBulkData] = useState('');
  const [bulkResult, setBulkResult] = useState(null);

  const bulkSubTabs = [
    { 
      id: 'creditfactuur', 
      label: 'Creditfactuur Particulier',
      description: 'Voor particuliere patiënten',
      columns: ['Factuurnummer', 'Bedrag', 'Beschrijving', 'Datum', 'Patiënt'],
      example: 'INV001	50.00	Creditnota behandeling	2025-01-15	Jan Jansen'
    },
    { 
      id: 'creditdeclaratie', 
      label: 'Creditdeclaratie Verzekeraar',
      description: 'Voor zorgverzekeraar declaraties',  
      columns: ['Declaratienummer', 'Zorgverzekeraar', 'Bedrag', 'Reden', 'Datum', 'Patiënt'],
      example: 'DECL001	VGZ	75.50	Dubbele declaratie	2025-01-14	Piet Pietersen'
    },
    { 
      id: 'correctiefactuur', 
      label: 'Correctiefactuur Verzekeraar',
      description: 'Voor zorgverzekeraar correcties',
      columns: ['Declaratienummer', 'Zorgverzekeraar', 'Oorspronkelijk Bedrag', 'Gecorrigeerd Bedrag', 'Reden', 'Datum'],
      example: 'DECL002	CZ	100.00	85.50	Tarief correctie	2025-01-13'
    }
  ];

  // Form state for creating corrections
  const [correctieForm, setCorrectieForm] = useState({
    correction_type: 'creditfactuur_particulier',
    original_invoice_number: '',
    amount: '',
    description: '',
    date: '',
    patient_name: ''
  });

  const tabs = [
    { id: 'create', label: 'Handmatig Toevoegen', icon: 'plus' },
    { id: 'bulk', label: 'Bulk Import', icon: 'upload' },
    { id: 'match', label: 'Koppelen', icon: 'link' },
    { id: 'overview', label: 'Overzicht', icon: 'list' }
  ];

  useEffect(() => {
    if (activeTab === 'match') {
      fetchUnmatchedCorrecties();
    } else if (activeTab === 'overview') {
      fetchAllCorrecties();
    }
  }, [activeTab]);

  const fetchAllCorrecties = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/correcties`);
      setCorrecties(response.data);
    } catch (error) {
      console.error('Error fetching correcties:', error);
      setError('Fout bij ophalen correcties');
    } finally {
      setLoading(false);
    }
  };

  const fetchUnmatchedCorrecties = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/correcties/unmatched`);
      setUnmatchedCorrecties(response.data);
    } catch (error) {
      console.error('Error fetching unmatched correcties:', error);
      setError('Fout bij ophalen ongekoppelde correcties');
    } finally {
      setLoading(false);
    }
  };

  const fetchSuggestions = async (correctieId) => {
    try {
      const response = await axios.get(`${API}/correcties/suggestions/${correctieId}`);
      setSuggestions(response.data);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      setSuggestions([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');

      await axios.post(`${API}/correcties`, {
        ...correctieForm,
        amount: parseFloat(correctieForm.amount)
      });

      setSuccess('Correctie succesvol toegevoegd');
      setCorrectieForm({
        correction_type: 'creditfactuur_particulier',
        original_invoice_number: '',
        amount: '',
        description: '',
        date: '',
        patient_name: ''
      });

      // Refresh data if needed
      if (activeTab === 'overview') {
        fetchAllCorrecties();
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Fout bij toevoegen correctie');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCorrectie = (correctie) => {
    setSelectedCorrectie(correctie);
    fetchSuggestions(correctie.id);
  };

  const handleMatch = async (correctieId, transactionId) => {
    try {
      await axios.post(`${API}/correcties/${correctieId}/match?original_transaction_id=${transactionId}`);
      setSuccess('Correctie succesvol gekoppeld');
      setSelectedCorrectie(null);
      setSuggestions([]);
      fetchUnmatchedCorrecties(); // Refresh
    } catch (error) {
      setError(error.response?.data?.detail || 'Fout bij koppelen correctie');
    }
  };

  const handleBulkImport = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      setBulkResult(null);

      let endpoint;
      switch(bulkSubTab) {
        case 'creditfactuur':
          endpoint = 'import-creditfactuur';
          break;
        case 'creditdeclaratie':
          endpoint = 'import-creditdeclaratie';
          break;
        case 'correctiefactuur':
          endpoint = 'import-correctiefactuur';
          break;
        default:
          endpoint = 'import-creditfactuur';
      }

      const response = await axios.post(`${API}/correcties/${endpoint}`, {
        data: bulkData
      });

      setBulkResult(response.data);
      setSuccess(`Import voltooid: ${response.data.successful_imports} correcties geïmporteerd, ${response.data.auto_matched} automatisch gekoppeld`);
      setBulkData('');

      // Refresh data if needed
      if (activeTab === 'overview') {
        fetchAllCorrecties();
      } else if (activeTab === 'match') {
        fetchUnmatchedCorrecties();
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Fout bij bulk import correcties');
      setBulkResult(null);
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
    return new Date(dateString).toLocaleDateString('nl-NL');
  };

  const getCorrectionTypeLabel = (type) => {
    const labels = {
      'creditfactuur_particulier': 'Creditfactuur (Particulier)',
      'creditdeclaratie_verzekeraar': 'Creditdeclaratie (Verzekeraar)',
      'correctiefactuur_verzekeraar': 'Correctiefactuur (Verzekeraar)'
    };
    return labels[type] || type;
  };

  const getIcon = (iconName) => {
    const icons = {
      plus: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      ),
      link: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      ),
      list: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      ),
      upload: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      )
    };
    return icons[iconName];
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 gradient-text">
            Correctie Manager
          </h2>
          <p className="text-slate-600 mt-1">
            Beheer creditfacturen, correctiefacturen en creditdeclaraties
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {getIcon(tab.icon)}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Feedback Messages */}
      {error && (
        <div className="error-state">
          {error}
        </div>
      )}

      {success && (
        <div className="success-state">
          {success}
        </div>
      )}

      {/* Create Correction Tab */}
      {activeTab === 'create' && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h3 className="text-lg font-semibold text-slate-900">
              Nieuwe Correctie Toevoegen
            </h3>
            <p className="text-sm text-slate-500">
              Voeg creditfacturen, correctiefacturen of creditdeclaraties toe
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Type Correctie
                </label>
                <select
                  value={correctieForm.correction_type}
                  onChange={(e) => setCorrectieForm({...correctieForm, correction_type: e.target.value})}
                  className="form-select"
                  required
                >
                  <option value="creditfactuur_particulier">Creditfactuur (Particulier)</option>
                  <option value="creditdeclaratie_verzekeraar">Creditdeclaratie (Verzekeraar)</option>
                  <option value="correctiefactuur_verzekeraar">Correctiefactuur (Verzekeraar)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Oorspronkelijk Factuurnummer
                </label>
                <input
                  type="text"
                  value={correctieForm.original_invoice_number}
                  onChange={(e) => setCorrectieForm({...correctieForm, original_invoice_number: e.target.value})}
                  className="form-input"
                  placeholder="Bijv. INV001"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Correctie Bedrag (€)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={correctieForm.amount}
                  onChange={(e) => setCorrectieForm({...correctieForm, amount: e.target.value})}
                  className="form-input"
                  placeholder="Bedrag dat afgetrokken wordt"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Datum
                </label>
                <input
                  type="date"
                  value={correctieForm.date}
                  onChange={(e) => setCorrectieForm({...correctieForm, date: e.target.value})}
                  className="form-input"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Beschrijving
                </label>
                <input
                  type="text"
                  value={correctieForm.description}
                  onChange={(e) => setCorrectieForm({...correctieForm, description: e.target.value})}
                  className="form-input"
                  placeholder="Beschrijving van de correctie..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Patiënt Naam (optioneel)
                </label>
                <input
                  type="text"
                  value={correctieForm.patient_name}
                  onChange={(e) => setCorrectieForm({...correctieForm, patient_name: e.target.value})}
                  className="form-input"
                  placeholder="Naam van de patiënt"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Opslaan...' : 'Correctie Toevoegen'}
            </button>
          </form>
        </div>
      )}

      {/* Bulk Import Tab */}
      {activeTab === 'bulk' && (
        <div className="space-y-6">
          <div className="modern-card">
            <div className="modern-card-header">
              <h3 className="text-lg font-semibold text-slate-900">
                Bulk Import Correcties
              </h3>
              <p className="text-sm text-slate-500">
                Kopieer en plak correctiegegevens voor automatische verwerking
              </p>
            </div>

            <form onSubmit={handleBulkImport} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Correctie Data
                </label>
                <div className="mb-3 p-3 bg-slate-50 rounded-lg text-sm text-slate-600">
                  <strong>Verwachte kolommen (gescheiden door tabs):</strong>
                  <br />
                  Type | Factuurnummer | Bedrag | Beschrijving | Datum | Patiënt
                  <br /><br />
                  <strong>Type opties:</strong>
                  <ul className="list-disc list-inside text-xs mt-1 space-y-1">
                    <li><strong>creditfactuur particulier</strong> - Voor particuliere patiënten</li>
                    <li><strong>creditdeclaratie verzekeraar</strong> - Voor zorgverzekeraar declaraties</li>
                    <li><strong>correctiefactuur verzekeraar</strong> - Voor zorgverzekeraar correcties</li>
                  </ul>
                </div>
                <textarea
                  value={bulkData}
                  onChange={(e) => setBulkData(e.target.value)}
                  className="form-textarea h-32"
                  placeholder="Type	INV001	50.00	Creditnota behandeling	2025-01-15	Jan Jansen
creditdeclaratie verzekeraar	INV002	25.50	Incorrecte declaratie	2025-01-14	Piet Pietersen"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading || !bulkData.trim()}
                className="btn-primary"
              >
                {loading ? 'Importeren...' : 'Correcties Importeren'}
              </button>
            </form>
          </div>

          {/* Import Results */}
          {bulkResult && (
            <div className="modern-card">
              <div className="modern-card-header">
                <h4 className="text-lg font-semibold text-slate-900">
                  Import Resultaten
                </h4>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-blue-600 font-medium">Totaal Correcties</p>
                  <p className="text-2xl font-bold text-blue-900">{bulkResult.total_corrections}</p>
                </div>
                
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm text-green-600 font-medium">Succesvol</p>
                  <p className="text-2xl font-bold text-green-900">{bulkResult.successful_imports}</p>
                </div>
                
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-sm text-purple-600 font-medium">Auto-gekoppeld</p>
                  <p className="text-2xl font-bold text-purple-900">{bulkResult.auto_matched}</p>
                </div>
                
                <div className="bg-red-50 p-4 rounded-lg">
                  <p className="text-sm text-red-600 font-medium">Mislukt</p>
                  <p className="text-2xl font-bold text-red-900">{bulkResult.failed_imports}</p>
                </div>
              </div>

              {bulkResult.errors && bulkResult.errors.length > 0 && (
                <div>
                  <h5 className="font-medium text-slate-900 mb-3">Import Fouten:</h5>
                  <div className="space-y-2">
                    {bulkResult.errors.map((error, index) => (
                      <div key={index} className="text-sm text-red-600 bg-red-50 p-2 rounded">
                        {error}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <p className="text-sm text-green-800">
                  <strong>Automatische matching:</strong> Het systeem heeft geprobeerd correcties automatisch te koppelen 
                  aan originele facturen op basis van factuurnummer, patiëntnaam en bedragovereenkomst.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Match Corrections Tab */}
      {activeTab === 'match' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Unmatched Corrections */}
          <div className="modern-card">
            <div className="modern-card-header">
              <h4 className="text-lg font-semibold text-slate-900">
                Ongekoppelde Correcties
              </h4>
              <span className="text-sm text-slate-500">
                {unmatchedCorrecties.length} correcties
              </span>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {unmatchedCorrecties.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  Alle correcties zijn gekoppeld
                </div>
              ) : (
                unmatchedCorrecties.map((correctie) => (
                  <div
                    key={correctie.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      selectedCorrectie?.id === correctie.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    onClick={() => handleSelectCorrectie(correctie)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-medium text-slate-900">
                        {formatCurrency(correctie.amount)}
                      </div>
                      <div className="text-sm text-slate-500">
                        {formatDate(correctie.date)}
                      </div>
                    </div>
                    
                    <div className="text-sm text-slate-600 mb-1">
                      <strong>Type:</strong> {getCorrectionTypeLabel(correctie.correction_type)}
                    </div>
                    
                    <div className="text-sm text-slate-600 mb-1">
                      <strong>Beschrijving:</strong> {correctie.description}
                    </div>

                    {correctie.original_invoice_number && (
                      <div className="text-sm text-slate-600">
                        <strong>Factuurnummer:</strong> {correctie.original_invoice_number}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Matching Suggestions */}
          <div className="modern-card">
            <div className="modern-card-header">
              <h4 className="text-lg font-semibold text-slate-900">
                Mogelijke Matches
              </h4>
              {selectedCorrectie && (
                <span className="text-sm text-slate-500">
                  Voor {formatCurrency(selectedCorrectie.amount)}
                </span>
              )}
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {!selectedCorrectie ? (
                <div className="text-center py-8 text-slate-500">
                  Selecteer een correctie om matches te zien
                </div>
              ) : suggestions.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  Geen mogelijke matches gevonden
                </div>
              ) : (
                suggestions.map((transaction) => (
                  <div
                    key={transaction.id}
                    className="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-all"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-medium text-slate-900">
                        {formatCurrency(transaction.amount)}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          transaction.match_score >= 80 ? 'bg-green-100 text-green-700' :
                          transaction.match_score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {transaction.match_score}% match
                        </span>
                        <span className="text-sm text-slate-500">
                          {formatDate(transaction.date)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="text-sm text-slate-600 mb-2">
                      <strong>Beschrijving:</strong> {transaction.description}
                    </div>

                    {transaction.match_reason && (
                      <div className="text-sm text-slate-600 mb-2">
                        <strong>Match reden:</strong> {transaction.match_reason}
                      </div>
                    )}
                    
                    {transaction.patient_name && (
                      <div className="text-sm text-slate-600 mb-2">
                        <strong>Patiënt:</strong> {transaction.patient_name}
                      </div>
                    )}

                    {transaction.invoice_number && (
                      <div className="text-sm text-slate-600 mb-3">
                        <strong>Factuurnummer:</strong> {transaction.invoice_number}
                      </div>
                    )}
                    
                    <div className="flex justify-between items-center mt-3">
                      <span className={`category-badge category-${transaction.category}`}>
                        {transaction.category.toUpperCase()}
                      </span>
                      
                      <button
                        onClick={() => handleMatch(selectedCorrectie.id, transaction.id)}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors btn-animation"
                      >
                        Koppelen
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="modern-card">
          <div className="modern-card-header">
            <h4 className="text-lg font-semibold text-slate-900">
              Alle Correcties
            </h4>
            <span className="text-sm text-slate-500">
              {correcties.length} correcties
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
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Bedrag
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Beschrijving
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {correcties.map((correctie) => (
                  <tr key={correctie.id}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                      {formatDate(correctie.date)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-900">
                      {getCorrectionTypeLabel(correctie.correction_type)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                      -{formatCurrency(correctie.amount)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-900 max-w-xs truncate">
                      {correctie.description}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                        correctie.matched 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {correctie.matched ? 'Gekoppeld' : 'Ongekoppeld'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {correcties.length === 0 && !loading && (
              <div className="text-center py-8 text-slate-500">
                Nog geen correcties geregistreerd
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CorrectieManager;