import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type OcrWaterBillDocument = HydratedDocument<OcrWaterBill>;

@Schema({ timestamps: true })
export class OcrWaterBill {
  @Prop({ type: Object, required: true })
  provider: Record<string, any>;

  @Prop({ type: Object, required: true })
  customer: Record<string, any>;

  @Prop({ type: Object, required: true })
  account_and_bill: Record<string, any>;

  @Prop({ type: Array, default: [] })
  meter_details: any[];

  @Prop({ type: Object, required: true })
  balance_details: Record<string, any>;

  @Prop()
  document_type: string;

  @Prop()
  success: boolean;
}

export const OcrWaterBillSchema =
  SchemaFactory.createForClass(OcrWaterBill);