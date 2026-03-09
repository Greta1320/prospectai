"""
ProspectAI Backend - app.py
API Flask para el sistema de prospección inteligente
Railway-ready con PostgreSQL y soporte para Playwright
"""
import os
import json
import threading
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from database import init_db, get_db, close_db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

# Inicializar DB al arrancar
with app.app_context():
    init_db()

# ─────────────────────────────────────────────────
# CAMPAIGNS
# ─────────────────────────────────────────────────

@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.id, c.nombre, c.nicho, c.ciudad, c.created_at,
               COUNT(l.id) as total_leads,
               COUNT(CASE WHEN l.opportunity_score >= 70 THEN 1 END) as hot_leads
        FROM campaigns c
        LEFT JOIN leads l ON l.campaign_id = c.id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    close_db(db)
    return jsonify([dict(zip(cols, row)) for row in rows])


@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    data = request.json
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO campaigns (nombre, nicho, ciudad) VALUES (%s, %s, %s) RETURNING id, nombre, nicho, ciudad, created_at",
        (data['nombre'], data.get('nicho', ''), data.get('ciudad', ''))
    )
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    db.commit()
    close_db(db)
    return jsonify(dict(zip(cols, row))), 201


@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM leads WHERE campaign_id = %s", (campaign_id,))
    cur.execute("DELETE FROM campaigns WHERE id = %s", (campaign_id,))
    db.commit()
    close_db(db)
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────────

@app.route('/api/campaigns/<int:campaign_id>/leads', methods=['GET'])
def get_leads(campaign_id):
    filter_type = request.args.get('filter', 'all')  # hot/warm/cold/all
    search = request.args.get('q', '')

    db = get_db()
    cur = db.cursor()

    conditions = ["campaign_id = %s"]
    params = [campaign_id]

    if filter_type == 'hot':
        conditions.append("opportunity_score >= 70")
    elif filter_type == 'warm':
        conditions.append("opportunity_score >= 40 AND opportunity_score < 70")
    elif filter_type == 'cold':
        conditions.append("opportunity_score < 40")

    if search:
        conditions.append("(nombre ILIKE %s OR phone ILIKE %s)")
        params += [f'%{search}%', f'%{search}%']

    where = " AND ".join(conditions)
    cur.execute(f"""
        SELECT * FROM leads WHERE {where}
        ORDER BY opportunity_score DESC
    """, params)

    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    close_db(db)
    return jsonify([dict(zip(cols, row)) for row in rows])


@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    data = request.json
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE leads SET stage = %s WHERE id = %s",
        (data.get('stage'), lead_id)
    )
    db.commit()
    close_db(db)
    return jsonify({'ok': True})


# ─────────────────────────────────────────────────
# SCRAPING (Server-Sent Events para progreso real)
# ─────────────────────────────────────────────────

@app.route('/api/campaigns/<int:campaign_id>/scrape', methods=['POST'])
def scrape_campaign(campaign_id):
    data = request.json
    query = data.get('query', '')
    max_results = int(data.get('max_results', 20))

    if not query:
        return jsonify({'error': 'query requerido'}), 400

    def generate():
        """SSE stream: emite progreso y guarda leads en DB."""
        import asyncio
        from scraper import run_scrape

        def emit(msg, type='info'):
            yield f"data: {json.dumps({'type': type, 'msg': msg})}\n\n"

        yield from emit(f"🚀 Iniciando prospección: {query}", 'start')

        db = get_db()
        leads_saved = 0
        hot_leads = 0

        async def do_scrape():
            nonlocal leads_saved, hot_leads
            async for lead in run_scrape(query, max_results):
                if lead.get('type') == 'progress':
                    yield f"data: {json.dumps({'type': 'progress', 'msg': lead['msg'], 'pct': lead.get('pct', 0)})}\n\n"
                elif lead.get('type') == 'lead':
                    # Guardar en DB
                    cur = db.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO leads 
                            (campaign_id, nombre, phone, website, address, category, 
                             rating, reviews, opportunity_score, whatsapp_link, maps_url, stage)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'new')
                            ON CONFLICT (campaign_id, maps_url) DO UPDATE SET
                                opportunity_score = EXCLUDED.opportunity_score,
                                phone = EXCLUDED.phone
                        """, (
                            campaign_id,
                            lead['nombre'], lead['phone'], lead['website'],
                            lead['address'], lead['category'], lead['rating'],
                            lead['reviews'], lead['opportunity_score'],
                            lead['whatsapp_link'], lead['maps_url']
                        ))
                        db.commit()
                        leads_saved += 1
                        if lead['opportunity_score'] >= 70:
                            hot_leads += 1
                    except Exception as e:
                        db.rollback()
                    yield f"data: {json.dumps({'type': 'lead', 'lead': lead})}\n\n"

        # Correr el async scraper en el loop del thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def wrapper():
            async for chunk in do_scrape():
                yield chunk

        # Collect all chunks
        chunks = []
        async def collect():
            async for chunk in wrapper():
                chunks.append(chunk)

        loop.run_until_complete(collect())
        loop.close()
        close_db(db)

        for chunk in chunks:
            yield chunk

        yield f"data: {json.dumps({'type': 'done', 'total': leads_saved, 'hot': hot_leads})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


# ─────────────────────────────────────────────────
# STATS GLOBALES
# ─────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM campaigns) as total_campaigns,
            (SELECT COUNT(*) FROM leads) as total_leads,
            (SELECT COUNT(*) FROM leads WHERE opportunity_score >= 70) as hot_leads,
            (SELECT COUNT(*) FROM leads WHERE stage = 'contacted') as contacted,
            (SELECT COUNT(*) FROM leads WHERE stage = 'meeting_booked') as meetings
    """)
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    close_db(db)
    return jsonify(dict(zip(cols, row)))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
