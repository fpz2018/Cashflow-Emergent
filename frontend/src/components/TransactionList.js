import React from 'react';

const TransactionList = ({ transactions, onEdit, onDelete, formatCurrency }) => {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const getTransactionTypeLabel = (type) => {
    const types = {
      income: 'Inkomst',
      expense: 'Uitgave', 
      credit: 'Credit',
      correction: 'Correctie'
    };
    return types[type] || type;
  };

  const getCategoryLabel = (category) => {
    const categories = {
      zorgverzekeraar: 'Zorgverzekeraar',
      particulier: 'Particulier',
      fysiofitness: 'FysioFitness', 
      orthomoleculair: 'Orthomoleculair',
      credit_declaratie: 'Credit Declaratie',
      creditfactuur: 'Creditfactuur',
      huur: 'Huur',
      materiaal: 'Materiaal',
      salaris: 'Salaris',
      overig: 'Overig'
    };
    return categories[category] || category;
  };

  const getAmountColor = (type, amount) => {
    if (type === 'income') return 'text-emerald-600';
    if (type === 'expense') return 'text-red-600';
    if (type === 'credit') return 'text-yellow-600';
    if (type === 'correction') return 'text-blue-600';
    return 'text-slate-600';
  };

  const getAmountPrefix = (type) => {
    if (type === 'expense') return '-';
    if (type === 'credit') return '-';
    return '+';
  };

  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center py-12" data-testid="no-transactions">
        <svg className="mx-auto h-12 w-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-slate-900">Geen transacties</h3>
        <p className="mt-1 text-sm text-slate-500">Begin met het toevoegen van een nieuwe transactie.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="transaction-list">
      {transactions.map((transaction, index) => (
        <div 
          key={transaction.id}
          className="flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 rounded-lg transition-all card-hover fade-in border border-slate-200"
          style={{ animationDelay: `${index * 0.05}s` }}
          data-testid={`transaction-item-${transaction.id}`}
        >
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              {/* Transaction Type Badge */}
              <span className={`category-badge ${
                transaction.type === 'income' ? 'category-zorgverzekeraar' :
                transaction.type === 'expense' ? 'category-expense' :
                transaction.type === 'credit' ? 'category-credit' :
                'bg-blue-100 text-blue-800'
              }`}>
                {getTransactionTypeLabel(transaction.type)}
              </span>

              {/* Category Badge */}
              <span className={`category-badge category-${transaction.category}`}>
                {getCategoryLabel(transaction.category)}
              </span>

              {/* Date */}
              <span className="text-xs text-slate-500">
                {formatDate(transaction.date)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-slate-900 mb-1">
                  {transaction.description}
                </h4>
                
                <div className="flex items-center gap-4 text-sm text-slate-600">
                  {transaction.patient_name && (
                    <span>Patiënt: {transaction.patient_name}</span>
                  )}
                  {transaction.invoice_number && (
                    <span>Factuur: {transaction.invoice_number}</span>
                  )}
                  {transaction.reconciled && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Afgehandeld
                    </span>
                  )}
                </div>
              </div>

              <div className="text-right">
                <p className={`text-lg font-bold ${getAmountColor(transaction.type, transaction.amount)}`}>
                  {getAmountPrefix(transaction.type)}{formatCurrency(Math.abs(transaction.amount))}
                </p>
                
                {transaction.notes && (
                  <p className="text-xs text-slate-500 mt-1 max-w-32 truncate" title={transaction.notes}>
                    {transaction.notes}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 ml-4">
            <button
              onClick={() => onEdit(transaction)}
              className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
              title="Bewerken"
              data-testid={`edit-transaction-${transaction.id}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>

            <button
              onClick={() => {
                if (window.confirm('Weet u zeker dat u deze transactie wilt verwijderen?')) {
                  onDelete(transaction.id);
                }
              }}
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
              title="Verwijderen"
              data-testid={`delete-transaction-${transaction.id}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default TransactionList;