export default function Dashboard() {
  return (
    <main className="min-h-screen bg-stone-100 px-6 py-12 text-slate-900">
      <section className="mx-auto max-w-4xl rounded-3xl bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-green-700">
          Agrisense
        </p>
        <h1 className="mt-4 text-4xl font-bold">Smart farming dashboard</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
          Your React frontend is wired and ready for charts, crop suggestions,
          and weather insights from the FastAPI backend.
        </p>
      </section>
    </main>
  );
}
