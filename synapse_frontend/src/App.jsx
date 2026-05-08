import './App.css'

function App() {
  return (
    <main className="app-shell">
      <section className="brand-panel" aria-labelledby="brand-title">
        <img className="brand-logo" src="/synapse-logo.svg" alt="Synapse AI" />
        <p className="eyebrow">Clinical risk intelligence</p>
        <h1 id="brand-title">Synapse AI</h1>
        <p className="brand-copy">
          Patient observation scoring powered by your deployed Model V3 API.
        </p>
      </section>
    </main>
  )
}

export default App
