import { useMemo, useState } from 'react'
import doctorImage from './assets/ai-doctor.svg'
import './App.css'

const PREDICT_URL =
  import.meta.env.VITE_PREDICT_URL ??
  'https://synapse-ai-z2rt.onrender.com/predict'

const fields = [
  {
    key: 'Body Height',
    label: 'Height',
    unit: 'cm',
    min: 0,
    step: 0.1,
    defaultValue: 168,
  },
  {
    key: 'Body Weight',
    label: 'Weight',
    unit: 'kg',
    min: 0,
    step: 0.1,
    defaultValue: 70,
  },
  {
    key: 'Body mass index (BMI) [Ratio]',
    label: 'Body mass index',
    unit: 'BMI',
    min: 0,
    step: 0.1,
    defaultValue: 24.8,
  },
  {
    key: 'Heart rate',
    label: 'Heart rate',
    unit: 'bpm',
    min: 0,
    step: 1,
    defaultValue: 115,
  },
  {
    key: 'Body temperature',
    label: 'Temperature',
    unit: 'C',
    min: 0,
    step: 0.1,
    defaultValue: 38.7,
  },
  {
    key: 'Pain severity - 0-10 verbal numeric rating [Score] - Reported',
    label: 'Pain severity',
    unit: 'score',
    min: 0,
    max: 10,
    step: 1,
    defaultValue: 6,
  },
  {
    key: 'Glucose [Mass/volume] in Blood',
    label: 'Blood glucose',
    unit: 'mg/dL',
    min: 0,
    step: 0.1,
    defaultValue: 145,
  },
  {
    key: 'Hemoglobin [Mass/volume] in Blood',
    label: 'Hemoglobin',
    unit: 'g/dL',
    min: 0,
    step: 0.1,
    defaultValue: 11.5,
  },
]

const buildInitialVitals = () =>
  fields.reduce((values, field) => {
    values[field.key] = String(field.defaultValue)
    return values
  }, {})

const formatRecommendation = (recommendation) => {
  if (!recommendation) return { headline: '', summary: [], sections: [] }

  const lines = recommendation
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const sections = []
  const summary = []
  let currentSection = null

  lines.forEach((line) => {
    const cleanLine = line.replace(/^-+\s*/, '')

    if (cleanLine.endsWith(':')) {
      currentSection = {
        title: cleanLine.replace(':', ''),
        items: [],
      }
      sections.push(currentSection)
      return
    }

    if (currentSection) {
      currentSection.items.push(cleanLine)
      return
    }

    summary.push(cleanLine)
  })

  return {
    headline: summary[0] ?? '',
    summary: summary.slice(1),
    sections,
  }
}

function App() {
  const [vitals, setVitals] = useState(buildInitialVitals)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const payload = useMemo(
    () =>
      fields.reduce((values, field) => {
        values[field.key] = Number(vitals[field.key])
        return values
      }, {}),
    [vitals],
  )

  const resultText = useMemo(() => {
    if (!result) return 'Ready for assessment'

    if (typeof result === 'string') return result

    const likelyKeys = ['risk_label', 'prediction', 'Prediction', 'result', 'risk', 'class']
    const matchingKey = likelyKeys.find((key) => key in result)
    if (matchingKey) return String(result[matchingKey])

    return 'Prediction received'
  }, [result])

  const recommendation =
    result && typeof result === 'object' && 'recommendation' in result
      ? String(result.recommendation)
      : ''

  const formattedRecommendation = formatRecommendation(recommendation)

  const outcomeClass = error
    ? 'is-error'
    : String(resultText).toLowerCase().includes('high')
      ? 'is-high'
      : result
        ? 'is-complete'
        : 'is-idle'

  const handleChange = (key, value) => {
    setVitals((currentVitals) => ({
      ...currentVitals,
      [key]: value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch(PREDICT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const contentType = response.headers.get('content-type') ?? ''
      const responseBody = contentType.includes('application/json')
        ? await response.json()
        : await response.text()

      if (!response.ok) {
        throw new Error(
          typeof responseBody === 'string'
            ? responseBody
            : responseBody.detail || responseBody.message || 'Prediction failed',
        )
      }

      setResult(responseBody)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to reach the prediction service.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setVitals(buildInitialVitals())
    setResult(null)
    setError('')
  }

  return (
    <main className="site-shell">
      <header className="site-header" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="Synapse AI home">
          <span className="brand-mark">
            <img src="/synapse-mark.svg" alt="" />
          </span>
          <span className="brand-copy">
            <strong>Synapse AI</strong>
            <small>Clinical risk intelligence</small>
          </span>
        </a>
        <nav className="header-actions" aria-label="Primary">
          <span className="status-pill">Model V3</span>
          <a className="header-link" href="#assessment">
            Start assessment
          </a>
        </nav>
      </header>

      <section className="hero-section">
        <div className="hero-copy">
          <p className="eyebrow">Clinical risk intelligence</p>
          <h1>Synapse AI</h1>
          <p>
            Enter core patient measurements, send them to the live prediction
            model, and review the returned assessment in one focused workspace.
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#assessment">
              Run prediction
            </a>
            <span className="endpoint-pill">POST /predict</span>
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <img src={doctorImage} alt="" />
          <div className="signal-card signal-card-top">
            <span>Heart rate</span>
            <strong>115 bpm</strong>
          </div>
          <div className="signal-card signal-card-bottom">
            <span>Temperature</span>
            <strong>38.7 C</strong>
          </div>
        </div>
      </section>

      <section className="assessment-section" id="assessment">
        <div className="section-heading">
          <p className="eyebrow">Patient assessment</p>
          <h2>Vitals and lab values</h2>
          <p>
            Review the patient observations, then run the live risk model.
          </p>
        </div>

        <div className="workspace-grid">
          <form className="input-panel" onSubmit={handleSubmit}>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Inputs</p>
                <h3>Clinical measurements</h3>
              </div>
              <span className="sample-badge">Sample loaded</span>
            </div>

            <div className="field-grid">
              {fields.map((field) => (
                <label className="field" key={field.key}>
                  <span>{field.label}</span>
                  <div className="input-wrap">
                    <input
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={vitals[field.key]}
                      onChange={(event) =>
                        handleChange(field.key, event.target.value)
                      }
                      required
                    />
                    <em>{field.unit}</em>
                  </div>
                  <small>{field.key}</small>
                </label>
              ))}
            </div>

            <div className="form-actions">
              <button className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? 'Predicting...' : 'Predict'}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                onClick={handleReset}
                disabled={isSubmitting}
              >
                Reset
              </button>
            </div>
          </form>

          <aside className={`result-panel ${outcomeClass}`} aria-live="polite">
            <div className="result-header">
              <p className="eyebrow">Model output</p>
              <h2>{error ? 'Request error' : resultText}</h2>
              <p>
                {error
                  ? error
                  : result
                    ? 'Assessment returned from the hosted Synapse AI model.'
                    : 'Submit the form to receive a prediction from the hosted model.'}
              </p>
            </div>

            {recommendation ? (
              <div className="recommendation-card">
                <div className="clinical-alert">
                  <span>Clinical recommendation</span>
                  <strong>{formattedRecommendation.headline || resultText}</strong>
                  {formattedRecommendation.summary.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>

                <div className="clinical-sections">
                  {formattedRecommendation.sections.map((section) => (
                    <section key={section.title} className="clinical-section">
                      <h3>{section.title}</h3>
                      <ul>
                        {section.items.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <span>Status</span>
                <strong>{isSubmitting ? 'Analyzing patient data' : 'Waiting for submission'}</strong>
              </div>
            )}

            <details className="raw-details">
              <summary>{result ? 'Raw API response' : 'Request preview'}</summary>
              <pre>
                {error
                  ? error
                  : result
                    ? JSON.stringify(result, null, 2)
                    : JSON.stringify(payload, null, 2)}
              </pre>
            </details>
          </aside>
        </div>
      </section>
    </main>
  )
}

export default App
