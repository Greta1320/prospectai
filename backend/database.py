"""
database.py — Gestión de PostgreSQL para ProspectAI
Compatible con Railway (DATABASE_URL automático) y local (.env)
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db():
    """Retorna una conexión a PostgreSQL."""
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Railway provee DATABASE_URL automáticamente
        # Railway usa 'postgres://' pero psycopg2 necesita 'postgresql://'
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(db_url)
    else:
        # Local con variables individuales
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', 5432),
            database=os.environ.get('DB_NAME', 'prospectai'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', '')
        )


def close_db(db):
    try:
        db.close()
    except:
        pass


def init_db():
    """Crea las tablas si no existen."""
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            nicho VARCHAR(200),
            ciudad VARCHAR(200),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
            nombre VARCHAR(500),
            phone VARCHAR(50),
            website TEXT,
            address TEXT,
            category VARCHAR(200),
            rating VARCHAR(10),
            reviews VARCHAR(20),
            opportunity_score INTEGER DEFAULT 0,
            whatsapp_link TEXT,
            maps_url TEXT,
            stage VARCHAR(50) DEFAULT 'new',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(campaign_id, maps_url)
        )
    """)

    # Índices para queries frecuentes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_campaign ON leads(campaign_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(opportunity_score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage)")

    db.commit()
    close_db(db)
    print("✅ Base de datos inicializada")
