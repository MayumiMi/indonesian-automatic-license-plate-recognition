import mysql from 'mysql2/promise';

export default async function handler(req, res) {
  const db = await mysql.createConnection({
    host: 'localhost',
    user: 'plate_api',
    password: 'api#sh1',
    database: 'automatic_gate',
  });

  try {
    const [rows] = await db.execute('SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT 100');
    res.status(200).json(rows);
  } catch (error) {
    res.status(500).json({ error: 'Database error' });
  } finally {
    await db.end();
  }
}
