import React from 'react';

const CashflowCards = ({ cashflowSummary, formatCurrency }) => {
  if (!cashflowSummary) {
    return (
      <div className="grid-responsive">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="modern-card animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-1/2 mb-3"></div>
            <div className="h-8 bg-slate-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Vandaag Cashflow',
      value: cashflowSummary.today?.net_cashflow || 0,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
        </svg>
      ),
      color: cashflowSummary.today?.net_cashflow >= 0 ? 'emerald' : 'red',
      testId: 'today-cashflow-card'
    },
    {
      title: 'Inkomsten Vandaag',
      value: cashflowSummary.today?.total_income || 0,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
        </svg>
      ),
      color: 'emerald',
      testId: 'today-income-card'
    },
    {
      title: 'Uitgaven Vandaag',
      value: cashflowSummary.today?.total_expenses || 0,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
        </svg>
      ),
      color: 'red',
      testId: 'today-expenses-card'
    },
    {
      title: 'Totaal Transacties',
      value: cashflowSummary.total_transactions || 0,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      color: 'blue',
      testId: 'total-transactions-card',
      isCount: true
    }
  ];

  return (
    <div className="grid-responsive" data-testid="cashflow-cards">
      {cards.map((card, index) => (
        <div 
          key={card.title}
          className="modern-card pulse-soft"
          data-testid={card.testId}
          style={{ animationDelay: `${index * 0.1}s` }}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-600 mb-2">
                {card.title}
              </p>
              <p className={`text-2xl font-bold ${
                card.color === 'emerald' ? 'text-emerald-600' :
                card.color === 'red' ? 'text-red-600' :
                card.color === 'blue' ? 'text-blue-600' :
                'text-slate-900'
              }`}>
                {card.isCount ? 
                  card.value.toLocaleString('nl-NL') : 
                  formatCurrency(card.value)
                }
              </p>
              
              {/* Percentage change indicator (placeholder for future) */}
              <div className="flex items-center mt-2">
                <span className={`text-xs px-2 py-1 rounded-full ${
                  card.value >= 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                }`}>
                  {card.value >= 0 ? '+' : ''}{((card.value / 1000) * 100).toFixed(1)}%
                </span>
                <span className="text-xs text-slate-500 ml-2">vs gisteren</span>
              </div>
            </div>
            
            <div className={`p-3 rounded-full ${
              card.color === 'emerald' ? 'bg-emerald-100 text-emerald-600' :
              card.color === 'red' ? 'bg-red-100 text-red-600' :
              card.color === 'blue' ? 'bg-blue-100 text-blue-600' :
              'bg-slate-100 text-slate-600'
            }`}>
              {card.icon}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default CashflowCards;