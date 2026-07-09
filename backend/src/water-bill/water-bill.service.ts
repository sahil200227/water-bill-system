import {
  Injectable,
  Logger,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as XLSX from 'xlsx';
import { CreateWaterBillDto } from './dto/create-water-bill.dto';
import { UpdateWaterBillDto } from './dto/update-water-bill.dto';
import { WaterBill, WaterBillDocument } from './schemas/water-bill.schema';

@Injectable()
export class WaterBillService {
  private readonly logger = new Logger(WaterBillService.name);

  constructor(
    @InjectModel(WaterBill.name)
    private readonly waterBillModel: Model<WaterBillDocument>,
  ) {}

  async create(createWaterBillDto: CreateWaterBillDto): Promise<WaterBill> {
    try {
      // ensure numeric fields and compute totalAmount server-side
      const prev = Number(createWaterBillDto.previousReading ?? 0);
      const curr = Number(createWaterBillDto.currentReading ?? 0);
      const charge = Number(createWaterBillDto.waterCharge ?? 0);
      const used = Math.max(curr - prev, 0);
      const totalAmount = used * charge;

      const doc = {
        ...createWaterBillDto,
        previousReading: prev,
        currentReading: curr,
        waterCharge: charge,
        totalAmount,
      } as CreateWaterBillDto & { totalAmount: number };

      const waterBill = new this.waterBillModel(doc);
      return await waterBill.save();
    } catch (error) {
      this.logger.error('Failed to create water bill', error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  async findAll(includeHidden = false): Promise<WaterBill[]> {
    try {
      const filter: any = {};
      if (!includeHidden) {
        filter.deleted = { $ne: true };
        filter.isPrivate = { $ne: true };
      }

      return await this.waterBillModel.find(filter).sort({ createdAt: -1 }).exec();
    } catch (error) {
      this.logger.error('Failed to fetch water bills', error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  async findOne(id: string, includeHidden = false): Promise<WaterBill> {
    try {
      const qb = this.waterBillModel.findById(id);

      const waterBill = await qb.exec();

      if (!waterBill) {
        throw new NotFoundException('Water bill not found');
      }

      if (!includeHidden && (waterBill.deleted || waterBill.isPrivate)) {
        throw new NotFoundException('Water bill not found');
      }

      return waterBill;
    } catch (error) {
      this.logger.error(`Failed to fetch water bill ${id}`, error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  async update(
    id: string,
    updateWaterBillDto: UpdateWaterBillDto,
  ): Promise<WaterBill> {
    try {
      const existing = await this.waterBillModel.findById(id).exec();
      if (!existing) throw new NotFoundException('Water bill not found');

      const prev = Number(updateWaterBillDto.previousReading ?? existing.previousReading ?? 0);
      const curr = Number(updateWaterBillDto.currentReading ?? existing.currentReading ?? 0);
      const charge = Number(updateWaterBillDto.waterCharge ?? existing.waterCharge ?? 0);
      const used = Math.max(curr - prev, 0);
      const totalAmount = used * charge;

      const merged: Partial<UpdateWaterBillDto & { totalAmount: number }> = {
        ...updateWaterBillDto,
        previousReading: prev,
        currentReading: curr,
        waterCharge: charge,
        totalAmount,
      };

      const waterBill = await this.waterBillModel.findByIdAndUpdate(id, merged, { new: true }).exec();
      if (!waterBill) throw new NotFoundException('Water bill not found');
      return waterBill;
    } catch (error) {
      this.logger.error(`Failed to update water bill ${id}`, error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  // Soft delete: mark as deleted but keep record
  async remove(id: string): Promise<{ message: string }> {
    try {
      const waterBill = await this.waterBillModel
        .findByIdAndUpdate(id, { deleted: true, deletedAt: new Date() }, { new: true })
        .exec();

      if (!waterBill) {
        throw new NotFoundException('Water bill not found');
      }

      return { message: 'Water bill soft-deleted successfully' };
    } catch (error) {
      this.logger.error(`Failed to delete water bill ${id}`, error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  // Hard delete: remove from DB entirely
  async hardRemove(id: string): Promise<{ message: string }> {
    try {
      const waterBill = await this.waterBillModel.findByIdAndDelete(id).exec();

      if (!waterBill) {
        throw new NotFoundException('Water bill not found');
      }

      return { message: 'Water bill permanently deleted' };
    } catch (error) {
      this.logger.error(`Failed to hard delete water bill ${id}`, error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }

  async importRecords(records: CreateWaterBillDto[]): Promise<WaterBill[]> {
    type ImportedRecord = {
      customerName: string;
      accountNumber: string;
      serviceAddress: string;
      billingDate: Date;
      dueDate: Date;
      previousReading: number;
      currentReading: number;
      waterCharge: number;
      totalAmount: number;
    };

    const normalizedRecords = records
      .filter((record) => record && Object.values(record).some((value) => value !== undefined && value !== ''))
      .map((record) => ({
        customerName: record.customerName?.toString().trim() ?? '',
        accountNumber: record.accountNumber?.toString().trim() ?? '',
        serviceAddress: record.serviceAddress?.toString().trim() ?? '',
        billingDate: record.billingDate ? new Date(record.billingDate) : undefined,
        dueDate: record.dueDate ? new Date(record.dueDate) : undefined,
        previousReading: Number(record.previousReading ?? 0),
        currentReading: Number(record.currentReading ?? 0),
        waterCharge: Number(record.waterCharge ?? 0),
        totalAmount: Number(record.totalAmount ?? 0),
      }))
      .filter(
        (record): record is ImportedRecord =>
          Boolean(record.customerName && record.accountNumber && record.billingDate && record.dueDate),
      );

    if (normalizedRecords.length === 0) {
      throw new BadRequestException('No valid water bill rows were found in the uploaded file');
    }

    const created = await this.waterBillModel.insertMany(normalizedRecords);
    this.logger.log(`Imported ${created.length} water bill records`);
    return created as unknown as WaterBill[];
  }

  async importFile(file: Express.Multer.File): Promise<{ message: string; imported: number }> {
    if (!file?.buffer?.length) {
      throw new BadRequestException('Please upload a CSV or Excel file');
    }

    try {
      const workbook = XLSX.read(file.buffer, { type: 'buffer' });
      const sheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json(worksheet, { defval: '' }) as CreateWaterBillDto[];

      const created = await this.importRecords(rows);
      return { message: 'Water bills imported successfully', imported: created.length };
    } catch (error) {
      this.logger.error('Failed to import water bills from file', error instanceof Error ? error.stack : undefined);
      throw error;
    }
  }
}
