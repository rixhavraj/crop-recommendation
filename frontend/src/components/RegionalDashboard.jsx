import { useState, useEffect } from "react";
import { api } from "../lib/api";

export default function RegionalDashboard() {
  const [regions, setRegions] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/regions")
      .then((res) => {
        setRegions(res.data);
        if (res.data.length > 0) setSelectedRegion(res.data[0]);
      })
      .catch(() => {
        setError("Could not load region list");
      });
  }, []);

  useEffect(() => {
    if (selectedRegion) {
      setLoading(true);
      setError(null);
      api.get(`/regional/${selectedRegion}`)
        .then((res) => {
          setData(res.data);
        })
        .catch(() => {
          setData(null);
          setError("Could not load regional insights");
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [selectedRegion]);

  return (
    <div className="glass-card p-6 animate-fade-in stagger-2 mt-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl">🗺️</span> Regional Agricultural Insights
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">Historical success and weather intelligence by zone</p>
        </div>
        <div className="flex gap-2 bg-[var(--bg-secondary)] p-1 rounded-xl border border-[var(--border)] overflow-x-auto max-w-full">
          {regions.map((r) => (
            <button
              key={r}
              onClick={() => setSelectedRegion(r)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                selectedRegion === r
                  ? "bg-[var(--accent)] text-[var(--bg-primary)] shadow-lg shadow-[var(--accent-glow)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-4 text-[var(--text-muted)]">
          <div className="w-10 h-10 border-4 border-[var(--border)] border-t-[var(--accent)] rounded-full animate-spin" />
          <p className="text-sm animate-pulse">Syncing regional databases...</p>
        </div>
      ) : error ? (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">
          {error}
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Top Recommendations Section */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="w-1.5 h-6 bg-[var(--accent)] rounded-full" />
              <h3 className="font-bold">ML Region Recommendations</h3>
            </div>
            <div className="space-y-4">
              {data.top_recommended_crops.map((crop, idx) => (
                <div key={crop.crop} className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 hover:border-[var(--accent-dim)] transition-all">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{crop.emoji || "🌱"}</span>
                      <div>
                        <h4 className="font-bold text-sm">{crop.crop}</h4>
                        <span className="text-[10px] uppercase text-[var(--text-muted)] font-mono">Rank #{idx+1}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[var(--accent)] text-xs font-bold">{crop.confidence}%</span>
                      <p className="text-[9px] text-[var(--text-muted)]">Confidence</p>
                    </div>
                  </div>
                  <div className="w-full bg-[var(--border)] h-1 rounded-full overflow-hidden mb-3">
                    <div className="bg-[var(--accent)] h-full rounded-full transition-all duration-1000" style={{ width: `${crop.confidence}%` }} />
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">{crop.reason}</p>
                </div>
              ))}
              {data.top_recommended_crops.length === 0 && (
                <div className="p-4 border border-dashed border-[var(--border)] rounded-xl text-center text-xs text-[var(--text-muted)]">
                  Predictive model is analyzing upcoming seasonal patterns...
                </div>
              )}
            </div>
          </div>

          {/* History & Statistics */}
          <div className="space-y-8">
             <section>
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-1.5 h-6 bg-[var(--info)] rounded-full" />
                  <h3 className="font-bold">Historical Success Rates</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {data.historical_success.map((h) => (
                    <div key={h.crop} className="bg-[var(--bg-secondary)]/50 border border-[var(--border)] rounded-xl p-3">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-bold font-mono">{h.crop}</span>
                        <span className="text-[10px] px-2 py-0.5 bg-[var(--accent-glow)] text-[var(--accent)] rounded-full">{h.success_rate}</span>
                      </div>
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="text-[var(--text-muted)]">Avg Profit</span>
                        <span className="text-[var(--text-primary)] font-bold">₹{h.avg_profit.toLocaleString()}</span>
                      </div>
                      <div className="mt-1 flex justify-between items-center text-[9px] text-[var(--text-muted)] italic">
                        <span>Best Year: {h.notable_year}</span>
                        <span>/ acre</span>
                      </div>
                    </div>
                  ))}
                </div>
             </section>

             <section className="bg-gradient-to-br from-[var(--bg-secondary)] to-transparent p-5 rounded-2xl border border-[var(--accent-dim)]/20">
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">☁️</span>
                    <h3 className="text-sm font-bold">Regional Climate Insights</h3>
                </div>
                <p className="text-xs text-[var(--text-secondary)] mb-4 leading-relaxed font-mono">
                  &gt; {data.weather_summary}
                </p>
                <div className="flex flex-wrap gap-2">
                   {data.states.map(s => (
                     <span key={s} className="text-[9px] px-2 py-1 bg-[var(--bg-card)] border border-[var(--border)] rounded-md text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors">
                        {s}
                     </span>
                   ))}
                </div>
             </section>
          </div>
        </div>
      ) : null}
    </div>
  );
}
