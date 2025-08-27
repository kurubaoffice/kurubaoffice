import React, { useEffect, useState } from "react";
import { getMarketSummary } from "../api/tidder-api.js";
import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import StockSearch from "../components/StockSearch";


export default function MarketSummary() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // Mock data for now
    setData({
      indices: [
        { symbol: "NIFTY50", price: 19500.25, changePercent: +0.8 },
        { symbol: "BANKNIFTY", price: 44120.75, changePercent: -0.5 },
      ],
      topStocks: [
        { symbol: "RELIANCE", price: 2700.5, changePercent: +1.8 },
        { symbol: "INFY", price: 1560.25, changePercent: -0.9 },
        { symbol: "HDFCBANK", price: 1620.1, changePercent: +2.3 },
      ],
    });
  }, []);

  if (!data) return <Loader />;

  return (
    <div className="p-6 space-y-10">
      {/* Page Heading */}
      <h1 className="text-3xl font-bold text-gray-800">Market Summary</h1>

      {/* Indices Section */}
      <section>
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Market Indices</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.indices.map((idx) => (
            <StockCard
              key={idx.symbol}
              title={idx.symbol}
              value={idx.price}
              change={idx.changePercent}
            />
          ))}
        </div>
      </section>

      {/* Top Stocks Section */}
      <section>
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Top Stocks</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.topStocks.map((stk) => (
            <StockCard
              key={stk.symbol}
              title={stk.symbol}
              value={stk.price}
              change={stk.changePercent}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

