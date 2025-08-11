import sqlite3

DB_PATH = "data/tidder.db"

def create_tables(conn):
    cursor = conn.cursor()

    # Table: stocks (basic list of symbols)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Table: company_info (core static fundamentals)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            market_cap REAL,
            pe_ratio REAL,
            eps REAL,
            pb_ratio REAL,
            promoter_holding REAL,
            institutional_holding REAL,
            roe REAL,
            last_updated TEXT
        )
    ''')

    # Table: price_data (daily price history)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY(symbol, date)
        )
    ''')

    # Table: technical_indicators (indicator values by date)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technical_indicators (
            symbol TEXT,
            date TEXT,
            indicator TEXT,
            value REAL,
            PRIMARY KEY(symbol, date, indicator)
        )
    ''')

    # Table: mutual_funds (optional - placeholder)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutual_funds (
            scheme_code TEXT PRIMARY KEY,
            scheme_name TEXT,
            fund_house TEXT
        )
    ''')

    # Table: mf_nav_history (optional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mf_nav_history (
            scheme_code TEXT,
            date TEXT,
            nav REAL,
            PRIMARY KEY(scheme_code, date)
        )
    ''')
    # Table: request_logs (new)
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_logs (
                id SERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,          -- 'telegram', 'cli', 'api'
                chat_id TEXT,                   -- Telegram chat/user ID if available
                request_type TEXT NOT NULL,     -- 'single_stock', 'nifty_index', etc.
                request_params TEXT,            -- JSON string of request params
                data_summary TEXT,              -- JSON summary of fetched data
                confidence_score REAL,
                elitewave_trend TEXT,
                elitewave_wave TEXT,
                elitewave_confidence REAL,
                full_report_sent BOOLEAN
            )
        ''')


    conn.commit()
    print("[INIT] All tables created or already exist.")

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    conn.close()
    print(f"[DONE] Schema initialized at {DB_PATH}")
