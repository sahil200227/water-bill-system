import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class RecordPaymentDto {
  @ApiProperty({ example: 500 })
  amount: number;

  @ApiPropertyOptional({ example: 'UPI' })
  method?: string;

  @ApiPropertyOptional({ example: 'TXN-123456' })
  reference?: string;
}
