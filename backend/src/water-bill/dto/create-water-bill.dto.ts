export class CreateWaterBillDto {
  customerName?: string;
  accountNumber?: string;
  serviceAddress?: string;
  billingDate?: string;
  dueDate?: string;
  previousReading?: number;
  currentReading?: number;
  waterCharge?: number;
  totalAmount?: number;
}
