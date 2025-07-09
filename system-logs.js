import mysql from 'mysql2/promise';

export default async function handler(req, res) {
  const db = await mysql.createConnection({
    host: 'localhost',
    user: 'plate_api',
    password: 'api#sh1',
    database: 'automatic_gate',
  });

  try {
    const [rows] = await db.execute('SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 50');
    res.status(200).json(rows);
  } catch (error) {
    console.error('Database error:', error);
    res.status(500).json({ error: 'Database error' });
  } finally {
    await db.end();
  }
}
