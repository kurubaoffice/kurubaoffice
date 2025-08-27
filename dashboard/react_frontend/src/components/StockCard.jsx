import React from "react";

export default function StockCard({ title, value, change }) {
  const positive = change >= 0;

  return (
    <div className="bg-white rounded-xl shadow-md p-4 flex flex-col gap-1">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="text-2xl font-bold text-gray-800">₹ {value}</p>
      <p
        className={`text-sm font-medium ${
          positive ? "text-green-600" : "text-red-600"
        }`}
      >
        {positive ? "▲" : "▼"} {change}%
      </p>
    </div>
  );
}

