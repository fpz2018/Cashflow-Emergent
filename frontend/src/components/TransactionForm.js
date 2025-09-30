import React, { useState, useEffect } from 'react';

const TransactionForm = ({ transaction, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    type: 'income',
    category: '',
    amount: '',
    description: '',
    date: new Date().toISOString().split('T')[0],
    patient_name: '',
    invoice_number: '',
    notes: ''
  });
  
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const incomeCategories = [
    { value: 'zorgverzekeraar', label: 'Zorgverzekeraar' },
    { value: 'particulier', label: 'Particulier' },
    { value: 'fysiofitness', label: 'FysioFitness' },
    { value: 'orthomoleculair', label: 'Orthomoleculaire Behandeling' },
    { value: 'credit_declaratie', label: 'Credit Declaratie' },
    { value: 'creditfactuur', label: 'Creditfactuur' }
  ];

  const expenseCategories = [
    { value: 'huur', label: 'Huur' },
    { value: 'materiaal', label: 'Materiaal' },
    { value: 'salaris', label: 'Salaris' },
    { value: 'overig', label: 'Overig' }
  ];

  const transactionTypes = [
    { value: 'income', label: 'Inkomst' },
    { value: 'expense', label: 'Uitgave' },
    { value: 'credit', label: 'Credit' },
    { value: 'correction', label: 'Correctie' }
  ];

  useEffect(() => {
    if (transaction) {
      setFormData({
        type: transaction.type || 'income',
        category: transaction.category || '',
        amount: transaction.amount?.toString() || '',
        description: transaction.description || '',
        date: transaction.date || new Date().toISOString().split('T')[0],
        patient_name: transaction.patient_name || '',
        invoice_number: transaction.invoice_number || '',
        notes: transaction.notes || ''
      });
    }
  }, [transaction]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.type) newErrors.type = 'Type is verplicht';
    if (!formData.category) newErrors.category = 'Categorie is verplicht';
    if (!formData.amount || isNaN(formData.amount) || parseFloat(formData.amount) <= 0) {
      newErrors.amount = 'Bedrag moet een geldig positief getal zijn';
    }
    if (!formData.description.trim()) newErrors.description = 'Beschrijving is verplicht';
    if (!formData.date) newErrors.date = 'Datum is verplicht';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    try {
      const submitData = {
        ...formData,
        amount: parseFloat(formData.amount)
      };

      await onSubmit(submitData);
    } catch (error) {
      console.error('Error submitting transaction:', error);
      setErrors({ submit: 'Er is een fout opgetreden bij het opslaan' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }

    // Reset category when type changes
    if (field === 'type') {
      setFormData(prev => ({ ...prev, category: '' }));
    }
  };

  const getAvailableCategories = () => {
    if (formData.type === 'income' || formData.type === 'credit') {
      return incomeCategories;
    }
    return expenseCategories;
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-900">
          {transaction ? 'Transactie Bewerken' : 'Nieuwe Transactie'}
        </h3>
        <button
          onClick={onCancel}
          className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
          data-testid="close-form-button"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {errors.submit && (
        <div className="error-state mb-4" data-testid="form-error">
          {errors.submit}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Transaction Type */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Type Transactie *
          </label>
          <select
            value={formData.type}
            onChange={(e) => handleChange('type', e.target.value)}
            className={`w-full input-modern ${errors.type ? 'border-red-500' : ''}`}
            data-testid="transaction-type-select"
          >
            {transactionTypes.map(type => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {errors.type && <p className="text-red-600 text-sm mt-1">{errors.type}</p>}
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Categorie *
          </label>
          <select
            value={formData.category}
            onChange={(e) => handleChange('category', e.target.value)}
            className={`w-full input-modern ${errors.category ? 'border-red-500' : ''}`}
            data-testid="category-select"
          >
            <option value="">Selecteer categorie</option>
            {getAvailableCategories().map(category => (
              <option key={category.value} value={category.value}>
                {category.label}
              </option>
            ))}
          </select>
          {errors.category && <p className="text-red-600 text-sm mt-1">{errors.category}</p>}
        </div>

        {/* Amount and Date Row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Bedrag (€) *
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.amount}
              onChange={(e) => handleChange('amount', e.target.value)}
              placeholder="0.00"
              className={`w-full input-modern ${errors.amount ? 'border-red-500' : ''}`}
              data-testid="amount-input"
            />
            {errors.amount && <p className="text-red-600 text-sm mt-1">{errors.amount}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Datum *
            </label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => handleChange('date', e.target.value)}
              className={`w-full input-modern ${errors.date ? 'border-red-500' : ''}`}
              data-testid="date-input"
            />
            {errors.date && <p className="text-red-600 text-sm mt-1">{errors.date}</p>}
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Beschrijving *
          </label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="Omschrijving van de transactie"
            className={`w-full input-modern ${errors.description ? 'border-red-500' : ''}`}
            data-testid="description-input"
          />
          {errors.description && <p className="text-red-600 text-sm mt-1">{errors.description}</p>}
        </div>

        {/* Patient Name and Invoice Number Row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Patiënt Naam
            </label>
            <input
              type="text"
              value={formData.patient_name}
              onChange={(e) => handleChange('patient_name', e.target.value)}
              placeholder="Optioneel"
              className="w-full input-modern"
              data-testid="patient-name-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Factuur Nummer
            </label>
            <input
              type="text"
              value={formData.invoice_number}
              onChange={(e) => handleChange('invoice_number', e.target.value)}
              placeholder="Optioneel"
              className="w-full input-modern"
              data-testid="invoice-number-input"
            />
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Notities
          </label>
          <textarea
            value={formData.notes}
            onChange={(e) => handleChange('notes', e.target.value)}
            placeholder="Extra notities (optioneel)"
            rows={3}
            className="w-full input-modern resize-none"
            data-testid="notes-textarea"
          />
        </div>

        {/* Form Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
            data-testid="cancel-button"
          >
            Annuleren
          </button>
          
          <button
            type="submit"
            disabled={loading}
            className={`px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium shadow-md hover:shadow-lg transition-all btn-animation ${
              loading ? 'opacity-70 cursor-not-allowed' : 'hover:from-blue-700 hover:to-indigo-700'
            }`}
            data-testid="submit-button"
          >
            {loading ? (
              <>
                <div className="spinner w-4 h-4 mr-2 inline-block"></div>
                Opslaan...
              </>
            ) : (
              <>
                {transaction ? 'Bijwerken' : 'Opslaan'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default TransactionForm;