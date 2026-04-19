// frontend/src/App.jsx
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import CropCard from "./components/CropCard";
import WeatherChart from "./components/WeatherChart";
import { api } from "./lib/api";

const MONTHS = [
  { value: 1, label: "January" },
  { value: 2, label: "February" },
  { value: 3, label: "March" },
  { value: 4, label: "April" },
  { value: 5, label: "May" },
  { value: 6, label: "June" },
  { value: 7, label: "July" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "October" },
  { value: 11, label: "November" },
  { value: 12, label: "December" },
];

const SOIL_TYPES = ["loam", "alluvial", "sandy", "clay", "silty", "black"];
const IRRIGATION_LEVELS = ["low", "medium", "high"];

export default function App() {
  const [district, setDistrict] = useState({ name: "Hisar", admin1: "Haryana", lat: 29.15, lon: 75.73 });
  const [month, setMonth] = useState(7);
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [soilType, setSoilType] = useState("loam");
  const [soilPh, setSoilPh] = useState(7.0);
  const [organicMatter, setOrganicMatter] = useState(1.3);
  const [irrigationLevel, setIrrigationLevel] = useState("medium");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState("checking");
  
  // Search state
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef(null);

  // Check API health and Geolocation on mount
  useEffect(() => {
    // API Health
    api
      .get("/health")
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));

    // User Geolocation
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setDistrict({ name: "Current Location", lat: latitude, lon: longitude });
        },
        () => console.log("Geolocation declined or failed")
      );
    }

    // Click outside handler
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle Search input
  useEffect(() => {
    if (search.length < 2) {
      setSuggestions([]);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await axios.get(
          `https://geocoding-api.open-meteo.com/v1/search?name=${search}&count=8&language=en&format=json&countrycode=in`
        );
        const results = (data.results || []).map(r => ({
          name: r.name,
          admin1: r.admin1,
          country: r.country,
          latitude: r.latitude,
          longitude: r.longitude,
          id: r.id
        }));
        setSuggestions(results);
        setShowSuggestions(true);
      } catch (e) {
        console.error("Geocoding failed", e);
      } finally {
        setSearching(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [search]);

  const [selectedCrop, setSelectedCrop] = useState(null);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResults([]);
    setSelectedCrop(null); // Reset selection on new search

    try {
      const { data } = await api.post("/recommend", {
        district: district.name,
        lat: district.lat,
        lon: district.lon,
        month,
        year,
        soil_type: soilType,
        soil_ph: Number(soilPh),
        organic_matter_pct: Number(organicMatter),
        irrigation_level: irrigationLevel,
      });
      setResults(data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          "Failed to get recommendations. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const selectLocation = (loc) => {
    setDistrict({
      name: loc.name,
      lat: loc.latitude,
      lon: loc.longitude,
      admin: loc.admin1
    });
    setSearch(loc.name);
    setShowSuggestions(false);
  };

  const handleUseMyLocation = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setDistrict({
          name: "Current Location",
          lat: pos.coords.latitude,
          lon: pos.coords.longitude
        });
        setSearch("");
      });
    }
  };

  const filteredResults = results.filter(r => r.crop !== selectedCrop?.crop);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background effects */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(52,211,153,0.08), transparent)",
        }}
      />
      <div className="fixed inset-0 dot-pattern pointer-events-none opacity-30" />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Hero */}
        <header className="mb-10 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">🌾</span>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
              <span className="gradient-text">AgriSense</span>
            </h1>
            <span
              className="w-2 h-2 rounded-full mt-1"
              style={{
                background: apiStatus === "online" ? "#34d399" : apiStatus === "offline" ? "#f87171" : "#fbbf24",
                boxShadow: apiStatus === "online" ? "0 0 8px rgba(52,211,153,0.5)" : "none",
              }}
            />
          </div>
          <p className="text-sm sm:text-base text-[var(--text-secondary)] max-w-xl leading-relaxed">
            AI-powered crop recommendation engine. Search any district to get intelligent
            suggestions based on historical weather patterns.
          </p>

          <div className="flex gap-4 mt-8 border-b border-[var(--border)] overflow-x-auto">
             <div className="pb-3 px-2 text-sm font-semibold text-[var(--accent)] relative">
                📍 Local Intelligence & Regional Analysis
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent)] rounded-full animate-fade-in" />
             </div>
          </div>
        </header>

        {/* Controls */}
        <div className="glass-card p-4 sm:p-5 mb-8 animate-fade-in shadow-xl shadow-black/20" style={{ animationDelay: "0.1s" }}>
          <div className="flex flex-wrap items-end gap-3">
                
                {/* Location Search */}
                <div className="flex-[2] min-w-[240px] relative" ref={searchRef}>
                  <label className="block text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5 font-semibold">
                    Search District / Location
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type="text"
                        placeholder="Search e.g. Hisar, Rohtak..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onFocus={() => search.length > 1 && setShowSuggestions(true)}
                        className="input-dark w-full pr-10"
                      />
                      {searching && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                          <span className="inline-block w-4 h-4 border-2 border-[var(--border)] border-t-[var(--accent)] rounded-full animate-spin" />
                        </div>
                      )}
                    </div>
                    <button 
                      onClick={handleUseMyLocation}
                      className="btn-geo"
                      title="Use My Location"
                    >
                      📍
                    </button>
                  </div>

                  {/* Suggestions Dropdown */}
                  {showSuggestions && suggestions.length > 0 && (
                    <div className="search-suggestions animate-fade-in">
                      {suggestions.map((loc) => (
                        <div
                          key={loc.id}
                          onClick={() => selectLocation(loc)}
                          className="suggestion-item border-b border-[var(--border)] last:border-0"
                        >
                          <span className="suggestion-name">{loc.name}</span>
                          <span className="suggestion-meta">
                            {loc.admin1}, {loc.country} • {loc.latitude.toFixed(2)}°N, {loc.longitude.toFixed(2)}°E
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Month */}
                <div className="flex-1 min-w-[140px]">
                  <label className="block text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5 font-semibold">
                    Planting Month
                  </label>
                  <select
                    value={month}
                    onChange={(e) => setMonth(+e.target.value)}
                    className="select-dark w-full"
                  >
                    {MONTHS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Year */}
                <div className="flex-1 min-w-[100px]">
                  <label className="block text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1.5 font-semibold">
                    Year
                  </label>
                  <select
                    value={year}
                    onChange={(e) => setYear(+e.target.value)}
                    className="select-dark w-full"
                  >
                    {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 1 - i).map(
                      (y) => (
                        <option key={y} value={y}>
                          {y}
                        </option>
                      )
                    )}
                  </select>
                </div>

                {/* Submit */}
                <button
                  onClick={handleSubmit}
                  disabled={loading || apiStatus === "offline"}
                  className="btn-glow text-sm whitespace-nowrap min-w-[140px]"
                  style={{ minHeight: 42 }}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="inline-block w-4 h-4 border-2 border-[var(--bg-primary)] border-t-transparent rounded-full animate-spin" />
                      Analyzing…
                    </span>
                  ) : (
                    "🔍 Analyze Crop"
                  )}
                </button>
              </div>

              {/* Selection Stats */}
              <div className="flex flex-wrap items-center gap-3 mt-4">
                <div className="stat-badge animate-fade-in">
                    Selected: <span className="text-[var(--accent)] font-bold ml-1">{district.name}</span>
                </div>
                <div className="stat-badge animate-fade-in">
                    Soil: <span className="text-[var(--accent)] font-bold ml-1">{soilType}</span>
                </div>
                <div className="stat-badge animate-fade-in">
                    Irrigation: <span className="text-[var(--accent)] font-bold ml-1">{irrigationLevel}</span>
                </div>
                <p className="text-[10px] text-[var(--text-muted)]">
                    {district.lat.toFixed(2)}°N, {district.lon.toFixed(2)}°E
                </p>
              </div>
            </div>

            {/* Results */}
            {error && (
              <div className="glass-card p-4 mb-6 border-red-500/20 bg-red-500/5 animate-fade-in">
                <p className="text-sm text-red-400 flex items-center gap-2">
                  <span>⚠️</span> {error}
                </p>
              </div>
            )}

            {results.length > 0 && (
              <section className="mb-12">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold">Recommended Intelligence</h2>
                  <span className="text-sm text-[var(--text-muted)]">{results.length} total options</span>
                </div>

                {/* Featured Selection (The Spreading Card) */}
                <div className={`mb-8 transition-all duration-700 ease-in-out ${selectedCrop ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4 hidden"}`}>
                  <CropCard 
                    data={selectedCrop || results[0]} 
                    isFeatured={true}
                    onSelect={() => setSelectedCrop(null)} 
                  />
                </div>

                {/* Grid of other options */}
                <div className={`mb-6 ${selectedCrop ? "mt-4 opacity-70" : "mt-0"}`}>
                   <h3 className="text-xs uppercase font-black tracking-widest text-[var(--text-muted)] mb-4 px-2">
                     {selectedCrop ? "Other Compatible Crops" : "Top Suggestions"}
                   </h3>
                   <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 items-start">
                      {(selectedCrop ? filteredResults : results).map((r, i) => (
                        <CropCard 
                          key={r.crop} 
                          data={r} 
                          index={i} 
                          onSelect={() => {
                            setSelectedCrop(r);
                            window.scrollTo({ top: 400, behavior: 'smooth' });
                          }} 
                        />
                      ))}
                   </div>
                </div>
              </section>
            )}

            {/* Weather Chart */}
            <section className="mb-8">
              <WeatherChart district={district} />
            </section>

            {/* Footer */}
            <footer className="text-center py-10 opacity-60">
               <p className="text-xs">AgriSense India • Premium Agricultural Intelligence v2.0</p>
            </footer>
          </div>
    </div>
  );
}
