import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type WaterBillDocument = HydratedDocument<WaterBill>;

@Schema({ timestamps: true })
export class WaterBill {
  @Prop({ required: true, trim: true })
  customerName: string;

  @Prop({ required: true, trim: true })
  accountNumber: string;

  @Prop({ required: true, trim: true })
  serviceAddress: string;

  @Prop({ required: true })
  billingDate: Date;

  @Prop({ required: true })
  dueDate: Date;

  @Prop({ required: true, min: 0 })
  previousReading: number;

  @Prop({ required: true, min: 0 })
  currentReading: number;

  @Prop({ required: true, min: 0 })
  waterCharge: number;

  @Prop({ required: true, min: 0 })
  totalAmount: number;
}

export const WaterBillSchema = SchemaFactory.createForClass(WaterBill);
