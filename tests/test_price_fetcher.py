import unittest
from storage import connection, db_reader
from fetcher import price_fetcher

class TestPriceFetcher(unittest.TestCase):

    def test_db_connection(self):
        conn = connection.get_connection()
        self.assertIsNotNone(conn)
        conn.close()

    def test_symbol_fetching(self):
        symbols = db_reader.get_active_symbols()
        self.assertIsInstance(symbols, list)
        self.assertGreater(len(symbols), 0)

    def test_fetch_and_store(self):
        price_fetcher.fetch_and_store_price("INFY.NS", start="2024-01-01")

if __name__ == '__main__':
    unittest.main()
