import React, { useEffect, useState } from "react";
import { getMarketData, getTopGainers, getTopLosers, getSectorPerformance } from "../api/tidder-api";

export default function Dashboard() {
  const [marketData, setMarketData] = useState({});
  const [topGainers, setTopGainers] = useState([]);
  const [topLosers, setTopLosers] = useState([]);
  const [sectorPerformance, setSectorPerformance] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [market, gainers, losers, sectors] = await Promise.all([
        getMarketData(),
        getTopGainers(),
        getTopLosers(),
        getSectorPerformance(),
      ]);
      setMarketData(market);
      setTopGainers(gainers);
      setTopLosers(losers);
      setSectorPerformance(sectors);
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData(); // initial fetch

    // Poll every 60 seconds
    const interval = setInterval(() => {
      fetchDashboardData();
    }, 60000);

    return () => clearInterval(interval); // cleanup on unmount
  }, []);

  if (loading) return <div className="p-6">Loading dashboard...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Market Dashboard</h1>

      {/* Market Overview */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(marketData).map(([key, value]) => (
          <div key={key} className="bg-white p-4 rounded-lg shadow flex justify-between items-center">
            <div>
              <p className="text-gray-500 uppercase">{key}</p>
              <p className="text-xl font-bold">₹{value.price ?? "-"}</p>
            </div>
            <div className={`text-lg font-semibold ${value.change >= 0 ? "text-green-600" : "text-red-600"}`}>
              {value.change >= 0 ? "+" : ""}
              {value.change?.toFixed(2)}%
            </div>
          </div>
        ))}
      </section>

      {/* Top Gainers & Losers */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Gainers */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Top Gainers</h2>
          <ul>
            {topGainers.map((stock) => (
              <li key={stock.symbol} className="flex justify-between border-b py-1">
                <span>{stock.name}</span>
                <span className="text-green-600">{stock.change >= 0 ? "+" : ""}{stock.change?.toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Top Losers */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Top Losers</h2>
          <ul>
            {topLosers.map((stock) => (
              <li key={stock.symbol} className="flex justify-between border-b py-1">
                <span>{stock.name}</span>
                <span className="text-red-600">{stock.change >= 0 ? "+" : ""}{stock.change?.toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Sector Performance */}
      <section className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Sector Performance</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {sectorPerformance.map((sector) => (
            <div key={sector.name} className="p-2 bg-gray-50 rounded flex justify-between">
              <span className="text-gray-600">{sector.name}</span>
              <span className={`font-semibold ${sector.performance >= 0 ? "text-green-600" : "text-red-600"}`}>
                {sector.performance >= 0 ? "+" : ""}
                {sector.performance?.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
