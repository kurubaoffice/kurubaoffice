import React, { useEffect, useState } from "react";
import Dashboard from "../pages/Dashboard.jsx";
import { getMarketSummary } from "../api/tidder-api.js";
import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import StockSearch from "../components/StockSearch";

export default function MarketSummary() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getMarketSummary().then(setData);
  }, []);

  if (!data) return <Loader />;

  const { indices, topStocks } = data; // Example structure

  const stockList = topStocks.map(s => s.symbol); // For search dropdown

  return (
    <div style={{ padding: "1rem" }}>
      <h1>Market Summary</h1>

      <StockSearch stockList={stockList} />

      <h2>Indices</h2>
      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {indices.map((idx) => (
          <StockCard key={idx.symbol} title={idx.symbol} value={idx.price} change={idx.change} />
        ))}
      </div>

      <h2>Top Stocks</h2>
      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {topStocks.map((s) => (
          <StockCard key={s.symbol} title={s.symbol} value={s.price} change={s.change} />
        ))}
      </div>
    </div>
  );
}
