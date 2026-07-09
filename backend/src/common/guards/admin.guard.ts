import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';

@Injectable()
export class AdminGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const adminKey = request.headers['x-admin-key'] as string | undefined;
    const expectedKey = process.env.ADMIN_KEY;

    if (!expectedKey || adminKey !== expectedKey) {
      throw new UnauthorizedException('Invalid or missing admin key');
    }

    return true;
  }
}
