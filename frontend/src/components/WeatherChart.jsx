// frontend/src/components/WeatherChart.jsx
import { useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from "recharts";
import { api } from "../lib/api";

const TABS = [
  { key: "rainfall", label: "Rainfall", unit: "mm", color: "#60a5fa" },
  { key: "temperature", label: "Temperature", unit: "°C", color: "#f87171" },
  { key: "water_balance", label: "Water Balance", unit: "mm", color: "#34d399" },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "rgba(10, 15, 13, 0.95)",
        border: "1px solid var(--border-glow)",
        borderRadius: 12,
        padding: "10px 14px",
        backdropFilter: "blur(8px)",
      }}
    >
      <p style={{ color: "var(--text-muted)", fontSize: 11, margin: 0 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color, fontSize: 13, fontWeight: 600, margin: "4px 0 0" }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

export default function WeatherChart({ district }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("rainfall");

  useEffect(() => {
    if (!district) return;
    setLoading(true);
    setError(null);

    api
      .get("/weather", {
        params: { lat: district.lat, lon: district.lon },
      })
      .then((res) => {
        setData(res.data.historical_trend || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Could not load weather data");
        setLoading(false);
      });
  }, [district]);

  const activeTab = TABS.find((t) => t.key === tab);

  return (
    <div className="glass-card p-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            Weather Trends — {district?.name}
          </h2>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Last 10 years of historical data
          </p>
        </div>

        {/* Tab pills */}
        <div className="flex gap-1 bg-[var(--bg-secondary)] rounded-xl p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-200"
              style={{
                background: tab === t.key ? t.color + "22" : "transparent",
                color: tab === t.key ? t.color : "var(--text-muted)",
                border: "none",
                cursor: "pointer",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div className="flex items-center justify-center h-[260px]">
          <div className="flex flex-col items-center gap-3">
            <div
              className="w-8 h-8 border-2 rounded-full"
              style={{
                borderColor: `${activeTab.color}33`,
                borderTopColor: activeTab.color,
                animation: "spin-slow 1s linear infinite",
              }}
            />
            <span className="text-xs text-[var(--text-muted)]">Loading weather data…</span>
          </div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-[260px] text-sm text-[var(--text-muted)]">
          {error}
        </div>
      ) : (
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            {tab === "rainfall" ? (
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={11} />
                <YAxis tick={{ fontSize: 10 }} unit=" mm" width={60} />
                <Tooltip content={<CustomTooltip />} />
                <Bar
                  dataKey="rainfall"
                  name="Rainfall"
                  fill={activeTab.color}
                  radius={[4, 4, 0, 0]}
                  fillOpacity={0.8}
                />
              </BarChart>
            ) : tab === "temperature" ? (
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={11} />
                <YAxis tick={{ fontSize: 10 }} unit="°C" width={50} />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="temp_max"
                  name="Max Temp"
                  stroke="#f87171"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="temp_min"
                  name="Min Temp"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            ) : (
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={11} />
                <YAxis tick={{ fontSize: 10 }} unit=" mm" width={60} />
                <Tooltip content={<CustomTooltip />} />
                <defs>
                  <linearGradient id="wbGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="water_balance"
                  name="Water Balance"
                  stroke="#34d399"
                  fill="url(#wbGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
      
      {/* Decade Stats Summary */}
      {!loading && data.length > 0 && (
        <div className="mt-6 pt-6 border-t border-[var(--border)] grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1">Avg Annual Rain</p>
            <p className="text-lg font-bold text-[var(--text-primary)]">
              {(data.reduce((acc, curr) => acc + curr.rainfall, 0) / (data.length / 12)).toFixed(0)} <span className="text-xs font-normal text-[var(--text-muted)]">mm</span>
            </p>
          </div>
          <div className="text-center border-x border-[var(--border)]">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1">Decade Avg Temp</p>
            <p className="text-lg font-bold text-[var(--text-primary)]">
              {(data.reduce((acc, curr) => acc + curr.temp_max, 0) / data.length).toFixed(1)} <span className="text-xs font-normal text-[var(--text-muted)]">°C</span>
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1">Peak Rainfall</p>
            <p className="text-lg font-bold text-[var(--text-primary)]">
              {Math.max(...data.map(d => d.rainfall)).toFixed(0)} <span className="text-xs font-normal text-[var(--text-muted)]">mm</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
