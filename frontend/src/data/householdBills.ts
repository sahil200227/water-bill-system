export type BillCategoryId = 'electricity' | 'water' | 'internet' | 'phone' | 'security' | 'pest-control';

export type UtilityBill = {
  id: string;
  utility: string;
  provider: string;
  category: BillCategoryId;
  period: string;
  dueDate: string;
  amount: number;
  status: 'Due' | 'Paid' | 'Overdue';
};

// Bill records are supplied by the API; no local sample records are retained.
export const householdBills: UtilityBill[] = [];

export const billCategories = [
  { id: 'electricity', label: 'Electricity', icon: '⚡' },
  { id: 'water', label: 'Water', icon: '◈' },
  { id: 'internet', label: 'Internet', icon: '◌' },
  { id: 'phone', label: 'Phone', icon: '☎' },
  { id: 'security', label: 'Security', icon: '⌾' },
  { id: 'pest-control', label: 'Pest Control', icon: '✦' },
] as const;

export const formatMoney = (amount: number) => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', minimumFractionDigits: 2,
}).format(amount);
