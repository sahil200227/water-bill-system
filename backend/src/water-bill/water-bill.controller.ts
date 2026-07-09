import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  Param,
  Patch,
  Post,
  Query,
  UploadedFile,
  UseGuards,
  UseInterceptors,
  UnauthorizedException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiHeader,
  ApiConsumes,
  ApiBody,
  ApiQuery,
  ApiParam,
  ApiSecurity,
} from '@nestjs/swagger';
import { CreateWaterBillDto } from './dto/create-water-bill.dto';
import { UpdateWaterBillDto } from './dto/update-water-bill.dto';
import { WaterBillService } from './water-bill.service';
import { AdminGuard } from '../common/guards/admin.guard';

@ApiTags('water-bill')
@ApiSecurity('x-admin-key')
@Controller('water-bill')
export class WaterBillController {
  constructor(private readonly waterBillService: WaterBillService) {}

  @Get()
  @ApiOperation({ summary: 'Get all water bills' })
  @ApiQuery({ name: 'admin', required: false, description: 'Include private and deleted records' })
  @ApiHeader({ name: 'x-admin-key', required: false, description: 'Admin secret key required if admin=true' })
  @ApiResponse({ status: 200, description: 'Successfully retrieved water bills' })
  getAll(@Query('admin') admin?: string, @Headers('x-admin-key') adminKey?: string) {
    if (admin === 'true' && adminKey !== process.env.ADMIN_KEY) {
      throw new UnauthorizedException('Invalid admin key');
    }

    const includeHidden = admin === 'true' && adminKey === process.env.ADMIN_KEY;
    return this.waterBillService.findAll(includeHidden);
  }

  @Post()
  @ApiOperation({ summary: 'Create a new water bill' })
  @ApiBody({ type: CreateWaterBillDto })
  @ApiResponse({ status: 201, description: 'Water bill created successfully' })
  create(@Body() createWaterBillDto: CreateWaterBillDto) {
    return this.waterBillService.create(createWaterBillDto);
  }

  @Post('import')
  @ApiOperation({ summary: 'Import water bills from CSV or Excel file' })
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        file: {
          type: 'string',
          format: 'binary',
          description: 'CSV or Excel file with water bill records',
        },
      },
    },
  })
  @ApiResponse({ status: 201, description: 'File imported successfully' })
  @UseInterceptors(FileInterceptor('file'))
  async importBills(@UploadedFile() file: Express.Multer.File) {
    return this.waterBillService.importFile(file);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a water bill by ID' })
  @ApiParam({ name: 'id', description: 'Water bill ID' })
  @ApiQuery({ name: 'admin', required: false, description: 'Include private and deleted records' })
  @ApiHeader({ name: 'x-admin-key', required: false, description: 'Admin secret key required if admin=true' })
  @ApiResponse({ status: 200, description: 'Water bill retrieved successfully' })
  getOne(
    @Param('id') id: string,
    @Query('admin') admin?: string,
    @Headers('x-admin-key') adminKey?: string,
  ) {
    if (admin === 'true' && adminKey !== process.env.ADMIN_KEY) {
      throw new UnauthorizedException('Invalid admin key');
    }

    const includeHidden = admin === 'true' && adminKey === process.env.ADMIN_KEY;
    return this.waterBillService.findOne(id, includeHidden);
  }

  @Get('admin/verify')
  @ApiOperation({ summary: 'Verify admin secret key' })
  @ApiHeader({ name: 'x-admin-key', required: true, description: 'Admin secret key' })
  @ApiResponse({ status: 200, description: 'Admin key is valid' })
  @ApiResponse({ status: 401, description: 'Invalid admin key' })
  verifyAdmin(@Headers('x-admin-key') adminKey?: string) {
    if (adminKey !== process.env.ADMIN_KEY) {
      throw new UnauthorizedException('Invalid admin key');
    }
    return { ok: true };
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update a water bill by ID' })
  @ApiParam({ name: 'id', description: 'Water bill ID' })
  @ApiBody({ type: UpdateWaterBillDto })
  @ApiResponse({ status: 200, description: 'Water bill updated successfully' })
  update(
    @Param('id') id: string,
    @Body() updateWaterBillDto: UpdateWaterBillDto,
  ) {
    return this.waterBillService.update(id, updateWaterBillDto);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Soft-delete a water bill by ID' })
  @ApiParam({ name: 'id', description: 'Water bill ID' })
  @ApiResponse({ status: 200, description: 'Water bill soft-deleted successfully' })
  remove(@Param('id') id: string) {
    return this.waterBillService.remove(id);
  }

  @UseGuards(AdminGuard)
  @Delete(':id/hard')
  @ApiOperation({ summary: 'Permanently delete a water bill by ID (requires admin key)' })
  @ApiParam({ name: 'id', description: 'Water bill ID' })
  @ApiHeader({ name: 'x-admin-key', required: true, description: 'Admin secret key' })
  @ApiResponse({ status: 200, description: 'Water bill permanently deleted' })
  hardRemove(@Param('id') id: string) {
    return this.waterBillService.hardRemove(id);
  }
}
