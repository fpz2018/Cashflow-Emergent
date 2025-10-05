import React, { useState, useEffect } from 'react';
import axios from 'axios';
import CorrectieManager from './CorrectieManager';
import DataCleanup from './DataCleanup';
import KostenOverzicht from './KostenOverzicht';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DataSetup = () => {
  const [activeSection, setActiveSection] = useState('banksaldo');
  const [bankSaldos, setBankSaldos] = useState([]);
  const [overigeOmzet, setOverigeOmzet] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Bank Saldo State
  const [bankSaldoForm, setBankSaldoForm] = useState({
    description: 'Startbanksaldo 1-1-2025',
    amount: '',
    date: '2025-01-01'
  });

  // Overige Omzet State
  const [omzetForm, setOmzetForm] = useState({
    description: '',
    amount: '',
    date: '',
    recurring: false
  });

  useEffect(() => {
    if (activeSection === 'banksaldo') {
      fetchBankSaldos();
    } else if (activeSection === 'omzet') {
      fetchOverigeOmzet();
    }
  }, [activeSection]);

  const fetchBankSaldos = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/bank-saldo`);
      setBankSaldos(response.data);
    } catch (error) {
      console.error('Error fetching bank saldos:', error);
      setError('Fout bij ophalen bank saldos');
    } finally {
      setLoading(false);
    }
  };

  const fetchOverigeOmzet = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/overige-omzet`);
      setOverigeOmzet(response.data);
    } catch (error) {
      console.error('Error fetching overige omzet:', error);
      setError('Fout bij ophalen overige omzet');
    } finally {
      setLoading(false);
    }
  };

  const handleBankSaldoSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      const formData = new FormData();
      formData.append('description', bankSaldoForm.description);
      formData.append('amount', parseFloat(bankSaldoForm.amount));
      formData.append('date', bankSaldoForm.date);

      await axios.post(`${API}/bank-saldo`, formData);
      setSuccess('Bank saldo succesvol toegevoegd');
      setBankSaldoForm({ description: 'Startbanksaldo 1-1-2025', amount: '', date: '2025-01-01' });
      fetchBankSaldos();
    } catch (error) {
      setError(error.response?.data?.detail || 'Fout bij toevoegen bank saldo');
    } finally {
      setLoading(false);
    }
  };

  const handleOmzetSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      const formData = new FormData();
      formData.append('description', omzetForm.description);
      formData.append('amount', parseFloat(omzetForm.amount));
      formData.append('date', omzetForm.date);
      formData.append('recurring', omzetForm.recurring);

      await axios.post(`${API}/overige-omzet`, formData);
      setSuccess('Overige omzet succesvol toegevoegd');
      setOmzetForm({ description: '', amount: '', date: '', recurring: false });
      fetchOverigeOmzet();
    } catch (error) {
      setError(error.response?.data?.detail || 'Fout bij toevoegen overige omzet');
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

  const sections = [
    { id: 'banksaldo', label: 'Bank Saldo', icon: 'bank' },
    { id: 'omzet', label: 'Overige Omzet', icon: 'plus' },
    { id: 'correcties', label: 'Correcties', icon: 'edit' },
    { id: 'kosten', label: 'Kosten Overzicht', icon: 'money' },
    { id: 'cleanup', label: 'Data Cleanup', icon: 'trash' }
  ];

  const getIcon = (iconName) => {
    const icons = {
      bank: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
        </svg>
      ),
      plus: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      ),
      edit: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
      ),
      money: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
        </svg>
      ),
      trash: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
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
            Data Setup
          </h2>
          <p className="text-slate-600 mt-1">
            Configureer basis gegevens voor cashflow prognose
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-all ${
                activeSection === section.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {getIcon(section.icon)}
              {section.label}
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

      {/* Bank Saldo Section */}
      {activeSection === 'banksaldo' && (
        <div className="space-y-6">
          <div className="modern-card">
            <div className="modern-card-header">
              <h3 className="text-lg font-semibold text-slate-900">
                Bank Saldo Instellen
              </h3>
              <p className="text-sm text-slate-500">
                Stel het startbanksaldo in voor accurate prognoses
              </p>
            </div>

            <form onSubmit={handleBankSaldoSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Beschrijving
                  </label>
                  <input
                    type="text"
                    value={bankSaldoForm.description}
                    onChange={(e) => setBankSaldoForm({...bankSaldoForm, description: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Bedrag (€)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={bankSaldoForm.amount}
                    onChange={(e) => setBankSaldoForm({...bankSaldoForm, amount: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Datum
                  </label>
                  <input
                    type="date"
                    value={bankSaldoForm.date}
                    onChange={(e) => setBankSaldoForm({...bankSaldoForm, date: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
              >
                {loading ? 'Opslaan...' : 'Bank Saldo Toevoegen'}
              </button>
            </form>
          </div>

          {/* Bank Saldos List */}
          <div className="modern-card">
            <div className="modern-card-header">
              <h3 className="text-lg font-semibold text-slate-900">
                Geregistreerde Bank Saldos
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Datum
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Saldo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                      Beschrijving
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {bankSaldos.map((saldo) => (
                    <tr key={saldo.id}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {formatDate(saldo.date)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {formatCurrency(saldo.saldo)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-900">
                        {saldo.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {bankSaldos.length === 0 && !loading && (
                <div className="text-center py-8 text-slate-500">
                  Nog geen bank saldos geregistreerd
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Overige Omzet Section */}
      {activeSection === 'omzet' && (
        <div className="space-y-6">
          <div className="modern-card">
            <div className="modern-card-header">
              <h3 className="text-lg font-semibold text-slate-900">
                Overige Omzet Toevoegen
              </h3>
              <p className="text-sm text-slate-500">
                Voeg overige inkomsten toe die niet via declaraties lopen
              </p>
            </div>

            <form onSubmit={handleOmzetSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Beschrijving
                  </label>
                  <input
                    type="text"
                    value={omzetForm.description}
                    onChange={(e) => setOmzetForm({...omzetForm, description: e.target.value})}
                    className="form-input"
                    placeholder="Beschrijving van de omzet..."
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Bedrag (€)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={omzetForm.amount}
                    onChange={(e) => setOmzetForm({...omzetForm, amount: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Datum
                  </label>
                  <input
                    type="date"
                    value={omzetForm.date}
                    onChange={(e) => setOmzetForm({...omzetForm, date: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={omzetForm.recurring}
                      onChange={(e) => setOmzetForm({...omzetForm, recurring: e.target.checked})}
                      className="form-checkbox h-4 w-4 text-blue-600"
                    />
                    <span className="ml-2 text-sm text-slate-700">
                      Terugkerende omzet (maandelijks)
                    </span>
                  </label>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
              >
                {loading ? 'Opslaan...' : 'Overige Omzet Toevoegen'}
              </button>
            </form>
          </div>

          {/* Overige Omzet List */}
          <div className="modern-card">
            <div className="modern-card-header">
              <h3 className="text-lg font-semibold text-slate-900">
                Geregistreerde Overige Omzet
              </h3>
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
                      Type
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {overigeOmzet.map((omzet) => (
                    <tr key={omzet.id}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {formatDate(omzet.date)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-900">
                        {formatCurrency(omzet.amount)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-900">
                        {omzet.description}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          omzet.recurring 
                            ? 'bg-blue-100 text-blue-700' 
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {omzet.recurring ? 'Terugkerend' : 'Eenmalig'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {overigeOmzet.length === 0 && !loading && (
                <div className="text-center py-8 text-slate-500">
                  Nog geen overige omzet geregistreerd
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Correcties Section */}
      {activeSection === 'correcties' && (
        <CorrectieManager />
      )}

      {/* Kosten Overzicht Section */}
      {activeSection === 'kosten' && (
        <KostenOverzicht />
      )}

      {/* Data Cleanup Section */}
      {activeSection === 'cleanup' && (
        <DataCleanup />
      )}
    </div>
  );
};

export default DataSetup;