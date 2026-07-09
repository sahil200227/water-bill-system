import { ApiPropertyOptional } from '@nestjs/swagger';

export class CreateWaterBillDto {
  @ApiPropertyOptional({ example: 'John Doe' })
  customerName?: string;

  @ApiPropertyOptional({ example: '367893568' })
  accountNumber?: string;

  @ApiPropertyOptional({ example: '123 Main St' })
  serviceAddress?: string;

  @ApiPropertyOptional({ example: '2026-07-09' })
  billingDate?: string;

  @ApiPropertyOptional({ example: '2026-07-30' })
  dueDate?: string;

  @ApiPropertyOptional({ example: 100 })
  previousReading?: number;

  @ApiPropertyOptional({ example: 200 })
  currentReading?: number;

  @ApiPropertyOptional({ example: 10 })
  waterCharge?: number;

  @ApiPropertyOptional({ example: 1000 })
  totalAmount?: number;

  @ApiPropertyOptional({ example: false })
  isPrivate?: boolean;
}
