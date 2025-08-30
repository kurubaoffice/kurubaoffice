import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Rectangle,
} from "recharts";

export default function Chart({ data, nameKey = "date" }) {
  // Check if data has OHLC
  const hasOHLC = data && data.length > 0 && data[0].open !== undefined;

  if (!data || data.length === 0) {
    return <div className="text-gray-500">No chart data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
      {hasOHLC ? (
        <ComposedChart data={data}>
          <XAxis dataKey={nameKey} />
          <YAxis />
          <Tooltip />
          {/* Wick (high-low line) */}
          <Bar
            dataKey="high"
            fill="transparent"
            shape={(props) => {
              const { x, y, width, height, payload } = props;
              const lowY = props.y + props.height;
              const highY = props.y;
              return (
                <line
                  x1={x + width / 2}
                  x2={x + width / 2}
                  y1={props.chartY}
                  y2={props.chartHeight}
                  stroke="#555"
                />
              );
            }}
          />
          {/* Candle body (open-close) */}
          {data.map((entry, index) => {
            const candleUp = entry.close >= entry.open;
            return (
              <Rectangle
                key={index}
                x={index * 20 + 10}
                y={Math.min(entry.open, entry.close)}
                width={8}
                height={Math.abs(entry.open - entry.close)}
                fill={candleUp ? "#4ade80" : "#f87171"} // green if up, red if down
              />
            );
          })}
        </ComposedChart>
      ) : (
        <LineChart data={data}>
          <XAxis dataKey={nameKey} />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="close" stroke="#3b82f6" />
        </LineChart>
      )}
    </ResponsiveContainer>
  );
}
