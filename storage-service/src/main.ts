import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: '*' });
  
  const port = process.env.PORT || 3003;
  await app.listen(port, '0.0.0.0');
  console.log(`Storage Service running on port ${port}`);
}
bootstrap();
