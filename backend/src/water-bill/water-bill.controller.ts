import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
} from '@nestjs/common';
import { CreateWaterBillDto } from './dto/create-water-bill.dto';
import { UpdateWaterBillDto } from './dto/update-water-bill.dto';
import { WaterBillService } from './water-bill.service';

@Controller('water-bill')
export class WaterBillController {
  constructor(private readonly waterBillService: WaterBillService) {}

  @Get()
  getAll() {
    return this.waterBillService.findAll();
  }

  @Post()
  create(@Body() createWaterBillDto: CreateWaterBillDto) {
    return this.waterBillService.create(createWaterBillDto);
  }

  @Get(':id')
  getOne(@Param('id') id: string) {
    return this.waterBillService.findOne(id);
  }

  @Patch(':id')
  update(
    @Param('id') id: string,
    @Body() updateWaterBillDto: UpdateWaterBillDto,
  ) {
    return this.waterBillService.update(id, updateWaterBillDto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.waterBillService.remove(id);
  }
}
