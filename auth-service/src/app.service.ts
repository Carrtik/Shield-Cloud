import { Injectable } from '@nestjs/common';
import { Pool } from 'pg';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { randomUUID } from 'crypto';

const JWT_SECRET = process.env.JWT_SECRET || 'shieldcloud_pqc_jwt_secret_2026';
const DB_URL = process.env.DATABASE_URL || 'postgresql://postgres_user:postgres_password@127.0.0.1:5432/shieldcloud';

const pool = new Pool({ connectionString: DB_URL });

@Injectable()
export class AppService {
  async register(email: string, name: string, password: string) {
    // Check if user exists
    const exists = await pool.query('SELECT id FROM users WHERE email = $1', [email]);
    if (exists.rows.length > 0) {
      throw new Error('Email already registered');
    }

    const id = randomUUID();
    const passwordHash = await bcrypt.hash(password, 12);

    await pool.query(
      `INSERT INTO users (id, email, password_hash, role) VALUES ($1, $2, $3, 'user')`,
      [id, email, passwordHash]
    );

    const token = jwt.sign({ id, email, name, role: 'user' }, JWT_SECRET, { expiresIn: '7d' });
    return { token, user: { id, email, name, role: 'user' } };
  }

  async login(email: string, password: string) {
    const result = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
    if (result.rows.length === 0) {
      throw new Error('Invalid email or password');
    }

    const user = result.rows[0];
    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) {
      throw new Error('Invalid email or password');
    }

    const name = email.split('@')[0]; // derive name from email for now
    const token = jwt.sign(
      { id: user.id, email: user.email, name, role: user.role },
      JWT_SECRET,
      { expiresIn: '7d' }
    );
    return { token, user: { id: user.id, email: user.email, name, role: user.role } };
  }

  verifyToken(token: string) {
    return jwt.verify(token, JWT_SECRET) as { id: string; email: string; name: string; role: string };
  }

  async getAllUsers() {
    const res = await pool.query(
      `SELECT id, email, role, created_at FROM users ORDER BY created_at DESC`
    );
    return { users: res.rows };
  }

  async changePassword(userId: string, currentPassword: string, newPassword: string) {
    const res = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
    if (res.rows.length === 0) throw new Error('User not found');
    const user = res.rows[0];
    const valid = await bcrypt.compare(currentPassword, user.password_hash);
    if (!valid) throw new Error('Current password is incorrect');
    const newHash = await bcrypt.hash(newPassword, 12);
    await pool.query('UPDATE users SET password_hash = $1 WHERE id = $2', [newHash, userId]);
    return { success: true, message: 'Password updated successfully' };
  }
}
