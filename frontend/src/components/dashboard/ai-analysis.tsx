import type { HardwareReport } from "@/hooks/use-live-data";
import Icon from "./dashboard-icon";

export default function AiAnalysis({ report }: { report: HardwareReport | null }) {
  return <section className="response-panel">
    <div className="response-heading"><span className="sensor-icon"><Icon name="sparkle"/></span><span>UN1C0RN^2 intelligence</span></div>
    <div className="response-status">{report ? "HARDWARE STATUS" : "HARDWARE DISCONNECTED"}</div>
    <h2>{report ? report.status : "Waiting for hardware"}</h2>
    <p>{report ? "Status and alerts reported by UN1C0RN^2." : "Connect your Pico to see live readings and hardware alerts."}</p>
    <div className="response-steps">{report?.alert_reasons.length ? report.alert_reasons.map(reason => <div key={reason}><span className="step-pending"/><span>{reason}</span></div>) : <div><span className="step-pending"/><span>{report ? "No hardware alerts reported" : "Alerts: null"}</span></div>}</div>
    <div className="model-score"><span>Isolation Forest score <strong>null</strong></span><small>No model score is available for this hardware report.</small></div>
  </section>;
}
