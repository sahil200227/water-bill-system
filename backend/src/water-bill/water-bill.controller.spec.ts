import { Test, TestingModule } from '@nestjs/testing';
import { WaterBillController } from './water-bill.controller';
import { WaterBillService } from './water-bill.service';

describe('WaterBillController', () => {
  let controller: WaterBillController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [WaterBillController],
      providers: [
        {
          provide: WaterBillService,
          useValue: {
            create: jest.fn(),
            findAll: jest.fn(),
            findOne: jest.fn(),
            update: jest.fn(),
            remove: jest.fn(),
          },
        },
      ],
    }).compile();

    controller = module.get<WaterBillController>(WaterBillController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
