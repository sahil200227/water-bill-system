import { WaterBillService } from './water-bill.service';

describe('WaterBillService', () => {
  let service: WaterBillService;
  let waterBillModel: any;

  beforeEach(() => {
    waterBillModel = {
      insertMany: jest.fn(),
      find: jest.fn(),
      findById: jest.fn(),
      findByIdAndUpdate: jest.fn(),
      findByIdAndDelete: jest.fn(),
    };

    service = new WaterBillService(waterBillModel);
  });

  it('imports valid water bills and normalizes values', async () => {
    const records = [
      {
        customerName: 'John Doe',
        accountNumber: '1001',
        serviceAddress: '12 Main St',
        billingDate: '2024-01-01',
        dueDate: '2024-01-10',
        previousReading: 10,
        currentReading: 15,
        waterCharge: 2,
        totalAmount: 10,
      },
    ];

    waterBillModel.insertMany.mockResolvedValue([{ _id: '1', ...records[0] }]);

    const result = await service.importRecords(records);

    expect(waterBillModel.insertMany).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          customerName: 'John Doe',
          totalAmount: 10,
        }),
      ]),
    );
    expect(result).toHaveLength(1);
  });
});
