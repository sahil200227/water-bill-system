import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { CreateWaterBillDto } from './dto/create-water-bill.dto';
import { UpdateWaterBillDto } from './dto/update-water-bill.dto';
import { WaterBill, WaterBillDocument } from './schemas/water-bill.schema';

@Injectable()
export class WaterBillService {
  constructor(
    @InjectModel(WaterBill.name)
    private readonly waterBillModel: Model<WaterBillDocument>,
  ) {}

  async create(createWaterBillDto: CreateWaterBillDto): Promise<WaterBill> {
    const waterBill = new this.waterBillModel(createWaterBillDto);
    return waterBill.save();
  }

  async findAll(): Promise<WaterBill[]> {
    return this.waterBillModel.find().sort({ createdAt: -1 }).exec();
  }

  async findOne(id: string): Promise<WaterBill> {
    const waterBill = await this.waterBillModel.findById(id).exec();

    if (!waterBill) {
      throw new NotFoundException('Water bill not found');
    }

    return waterBill;
  }

  async update(
    id: string,
    updateWaterBillDto: UpdateWaterBillDto,
  ): Promise<WaterBill> {
    const waterBill = await this.waterBillModel
      .findByIdAndUpdate(id, updateWaterBillDto, { new: true })
      .exec();

    if (!waterBill) {
      throw new NotFoundException('Water bill not found');
    }

    return waterBill;
  }

  async remove(id: string): Promise<{ message: string }> {
    const waterBill = await this.waterBillModel.findByIdAndDelete(id).exec();

    if (!waterBill) {
      throw new NotFoundException('Water bill not found');
    }

    return { message: 'Water bill deleted successfully' };
  }
}
