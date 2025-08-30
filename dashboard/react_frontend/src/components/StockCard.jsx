// src/components/StockCard.jsx
import React from "react";

export default function StockCard({ title, value, change, extra }) {
  return (
    <div className="bg-white p-4 rounded-xl shadow-md space-y-2">
      {/* Title */}
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>

      {/* Value */}
      <p className="text-xl font-semibold text-gray-800">
        {typeof value === "number" ? value.toFixed(2) : value}
      </p>

      {/* Change (if available) */}
      {change !== null && change !== undefined && (
        <p
          className={`text-sm font-medium ${
            change >= 0 ? "text-green-600" : "text-red-600"
          }`}
        >
          {change >= 0 ? "▲" : "▼"} {change}%
        </p>
      )}

      {/* Extra info (interpretation) */}
      {extra && <p className="text-sm text-gray-600 italic">{extra}</p>}
    </div>
  );
}
