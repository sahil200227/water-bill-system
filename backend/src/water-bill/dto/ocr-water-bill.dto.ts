export class OcrWaterBillDto {
  success: boolean;
  document_type: string;

  provider: {
    provider_name: string;
    provider_address: string;
  };

  customer: {
    customer_name: string;
    customer_id: string;
    service_location: string;
  };

  account_and_bill: {
    bill_number: string;
    bill_date: string;
    account_number: string;
    account_type: string;
    due_date: string;
  };

  meter_details: any[];

  balance_details: {
    previous_balance: string;
    adjustments: string;
    total_current_billing: string;
    amount_due: string;
    less_payments_received: string;
    penalties: string;
    deposit_applied: string;
  };
}