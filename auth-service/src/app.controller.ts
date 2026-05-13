import { Controller, Get, Post, Body, Headers, UnauthorizedException, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller('auth')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('health/live')
  livenessProbe() { return { status: 'alive' }; }

  @Get('health/ready')
  readinessProbe() { return { status: 'ready' }; }

  @Post('register')
  async register(@Body() body: { email: string; name: string; password: string }) {
    if (!body.email || !body.password) {
      throw new BadRequestException('Email and password are required');
    }
    try {
      return await this.appService.register(body.email, body.name || body.email.split('@')[0], body.password);
    } catch (e: any) {
      throw new BadRequestException(e.message);
    }
  }

  @Post('login')
  async login(@Body() body: { email: string; password: string }) {
    if (!body.email || !body.password) {
      throw new BadRequestException('Email and password are required');
    }
    try {
      return await this.appService.login(body.email, body.password);
    } catch (e: any) {
      throw new UnauthorizedException(e.message);
    }
  }

  @Get('me')
  getMe(@Headers('authorization') auth: string) {
    if (!auth?.startsWith('Bearer ')) {
      throw new UnauthorizedException('No token');
    }
    try {
      const user = this.appService.verifyToken(auth.slice(7));
      return { user };
    } catch {
      throw new UnauthorizedException('Invalid token');
    }
  }

  @Get('users')
  async getUsers(@Headers('authorization') auth: string) {
    if (!auth?.startsWith('Bearer ')) throw new UnauthorizedException('No token');
    try {
      const caller = this.appService.verifyToken(auth.slice(7));
      if (caller.role !== 'admin') throw new UnauthorizedException('Admin only');
    } catch {
      throw new UnauthorizedException('Invalid token or insufficient role');
    }
    try {
      return await this.appService.getAllUsers();
    } catch (e: any) {
      throw new BadRequestException(e.message);
    }
  }

  @Post('change-password')
  async changePassword(
    @Headers('authorization') auth: string,
    @Body() body: { currentPassword: string; newPassword: string },
  ) {
    if (!auth?.startsWith('Bearer ')) throw new UnauthorizedException('No token');
    let userId: string;
    try {
      const payload = this.appService.verifyToken(auth.slice(7));
      userId = payload.id;
    } catch {
      throw new UnauthorizedException('Invalid token');
    }
    if (!body.currentPassword || !body.newPassword) {
      throw new BadRequestException('currentPassword and newPassword are required');
    }
    if (body.newPassword.length < 6) {
      throw new BadRequestException('New password must be at least 6 characters');
    }
    try {
      return await this.appService.changePassword(userId, body.currentPassword, body.newPassword);
    } catch (e: any) {
      throw new BadRequestException(e.message);
    }
  }
}
