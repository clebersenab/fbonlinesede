import { neon } from '@neondatabase/serverless';
import { timingSafeEqual, createDecipheriv } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import seed from './_seed.js';

function igual(a, b) {
  if (!a || !b) return false;
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
}

function dadosIniciais(chave) {
  if (!chave || !seed || !seed.data) return null;
  try {
    const d = createDecipheriv('aes-256-gcm', Buffer.from(chave, 'hex'), Buffer.from(seed.iv, 'base64'));
    d.setAuthTag(Buffer.from(seed.tag, 'base64'));
    const gz = Buffer.concat([d.update(Buffer.from(seed.data, 'base64')), d.final()]);
    return JSON.parse(gunzipSync(gz).toString('utf8'));
  } catch (e) { console.error('seed', e.message); return null; }
}

function valido(d) {
  return d && typeof d === 'object' && Array.isArray(d.meses) && Array.isArray(d.colaboradores) && d.meses.length > 0;
}

export async function handle(req, res, sql, env) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex, nofollow');
  if (!sql) return res.status(500).json({ erro: 'Banco de dados não configurado na Vercel (DATABASE_URL).' });
  if (!env.ACCESS_PASSWORD || !env.ADMIN_PASSWORD) return res.status(500).json({ erro: 'Senhas não configuradas na Vercel (ACCESS_PASSWORD e ADMIN_PASSWORD).' });

  const senha = req.headers['x-senha'];
  const admin = igual(senha, env.ADMIN_PASSWORD);
  const leitura = admin || igual(senha, env.ACCESS_PASSWORD);

  await sql`create table if not exists banco_horas (
    id serial primary key,
    criado_em timestamptz not null default now(),
    payload jsonb not null
  )`;

  if (req.method === 'GET') {
    if (!leitura) return res.status(401).json({ erro: 'Senha incorreta.' });
    let r = await sql`select id, criado_em, payload from banco_horas order by id desc limit 1`;
    const ini = dadosIniciais(env.SEED_KEY);
    if (valido(ini) && (!r.length || (ini.revisao || 0) > (r[0].payload.revisao || 0))) {
      {
        await sql`insert into banco_horas (payload) values (${JSON.stringify(ini)}::jsonb)`;
        r = await sql`select id, criado_em, payload from banco_horas order by id desc limit 1`;
      }
    }
    if (!r.length) return res.status(404).json({ erro: 'Ainda não há dados no banco.' });
    return res.status(200).json({ versao: r[0].id, atualizado_em: r[0].criado_em, dados: r[0].payload });
  }

  if (req.method === 'POST') {
    if (!admin) return res.status(401).json({ erro: 'Senha de administrador incorreta.' });
    let body = req.body;
    if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = null; } }
    if (!valido(body)) return res.status(400).json({ erro: 'Arquivo fora do formato do banco de horas.' });
    const r = await sql`insert into banco_horas (payload) values (${JSON.stringify(body)}::jsonb) returning id, criado_em`;
    return res.status(201).json({ versao: r[0].id, atualizado_em: r[0].criado_em });
  }

  res.setHeader('Allow', 'GET, POST');
  return res.status(405).json({ erro: 'Método não permitido.' });
}

export default async function handler(req, res) {
  const url = process.env.DATABASE_URL || process.env.POSTGRES_URL;
  try {
    return await handle(req, res, url ? neon(url) : null, process.env);
  } catch (e) {
    console.error(e);
    return res.status(500).json({ erro: 'Erro no servidor ao acessar o banco de dados.' });
  }
}
