import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('auth-sessions')
export class SessionWorker extends WorkerHost {
  async process(job: Job<any, any, string>): Promise<any> {
    console.log(`Processing job ${job.id} of type ${job.name}`);
    
    // Simulate background task like geolocation logging or email notification
    switch (job.name) {
      case 'log-session':
        console.log('Logging session details:', job.data);
        // DB logging simulation
        break;
      case 'send-welcome':
        console.log('Sending welcome email to:', job.data.email);
        break;
      default:
        console.warn('Unknown job type:', job.name);
    }
  }
}
