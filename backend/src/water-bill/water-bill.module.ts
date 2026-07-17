import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { WaterBill, WaterBillSchema } from './schemas/water-bill.schema';
import {
  OcrWaterBill,
  OcrWaterBillSchema,
} from './schemas/ocr-water-bill.schema';
import { WaterBillController } from './water-bill.controller';
import { WaterBillService } from './water-bill.service';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: WaterBill.name, schema: WaterBillSchema },
      { name: OcrWaterBill.name, schema: OcrWaterBillSchema }, 
    ]),
  ],
  controllers: [WaterBillController],
  providers: [WaterBillService],
})
export class WaterBillModule {}