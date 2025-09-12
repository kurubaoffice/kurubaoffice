import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getStockAnalysis, getStockList } from "../api/tidder-api.js";

import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import Chart from "../components/Chart";

// uvicorn api.main:app --reload --port 8000
export default function StockAnalysis() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [stockList, setStockList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);

  // Fetch stock list on mount
  useEffect(() => {
    getStockList()
      .then((list) => {
        console.log("Fetched stock list:", list);
        setStockList(list || []);
      })
      .catch((err) => {
        console.error("Error fetching stock list:", err);
        setStockList([]);
      })
      .finally(() => setLoadingList(false));
  }, []);

  // Fetch stock analysis when symbol changes
  useEffect(() => {
    if (!symbol) return;

    async function fetchData() {
      try {
        const result = await getStockAnalysis(symbol);
        setData(result);
      } catch (err) {
        console.error("Error fetching stock data:", err);
      }
    }

    fetchData();
  }, [symbol]);

  // Case: no symbol selected yet
  if (!symbol) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold mb-4">Stock Analysis</h1>

        {loadingList ? (
          <p>Loading stock list...</p>
        ) : (
          <select
            defaultValue=""
            onChange={(e) => navigate(`/stock/${e.target.value}`)}
            className="border rounded-lg px-3 py-2 shadow-sm"
          >
            <option value="" disabled>
              -- Select Stock --
            </option>
            {stockList.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.name} ({s.symbol})
              </option>
            ))}
          </select>
        )}
      </div>
    );
  }

  // Case: symbol selected but still loading data
  if (!data) return <Loader />;

  const {
    price,
    changePercent,
    dayHigh,
    dayLow,
    yearHigh,
    yearLow,
    marketCap,
    volume,
    avgVolume,
    history,
    indicators,
    insights,
  } = data;

  return (
    <div className="p-6 space-y-10">
      {/* Heading + Dropdown */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800">
          Stock Analysis: <span className="text-blue-600">{symbol}</span>
        </h1>

        <select
          value={symbol}
          onChange={(e) => navigate(`/stock/${e.target.value}`)}
          className="border rounded-lg px-3 py-2 shadow-sm focus:ring focus:ring-blue-300"
        >
          <option value="" disabled>
            -- Select Stock --
          </option>
          {stockList.map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.name} ({s.symbol})
            </option>
          ))}
        </select>
      </div>

      {/* Overview Card */}
      <div className="bg-white shadow-lg rounded-xl p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Overview</h2>

        {/* Horizontal grid layout */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-gray-700">
          <div>
            <strong>Price:</strong> ₹{price}
          </div>
          <div>
            <strong>Change:</strong>{" "}
            <span className={changePercent > 0 ? "text-green-600" : "text-red-600"}>
              {changePercent}%
            </span>
          </div>
          <div>
            <strong>Day High:</strong> ₹{dayHigh}
          </div>
          <div>
            <strong>Day Low:</strong> ₹{dayLow}
          </div>
          <div>
            <strong>52W High:</strong> ₹{yearHigh}
          </div>
          <div>
            <strong>52W Low:</strong> ₹{yearLow}
          </div>
          <div>
            <strong>Market Cap:</strong> ₹{data.marketCap ?? "-"}
          </div>
          <div>
            <strong>PE Ratio:</strong> {data.peRatio ?? "-"}
          </div>
          <div>
            <strong>ROE:</strong> {data.roe != null ? data.roe + "%" : "-"}%
          </div>
          <div>
            <strong>EPS:</strong> {data.eps ?? "-"}
          </div>
          <div>
            <strong>Promoter Holding:</strong> {data.promoterHolding != null ? data.promoterHolding + "%" : "-"}%
          </div>
          <div>
            <strong>Institutional Holding:</strong> {data.institutionalHolding != null ? data.institutionalHolding + "%" : "-"}%
          </div>
          <div>
            <strong>Last Updated:</strong> {data.lastUpdated}
          </div>
        </div>
      </div>

      {/* Later: Indicators, Chart, Insights, etc. */}
    </div>
  );
}
