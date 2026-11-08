import type { HardwareReport } from "@/hooks/use-live-data";
import Icon from "./dashboard-icon";

<<<<<<< HEAD
export default function AiAnalysis({ report }: { report: HardwareReport | null }) {
  return <section className="response-panel">
    <div className="response-heading"><span className="sensor-icon"><Icon name="sparkle"/></span><span>UN1C0RN^2 intelligence</span></div>
    <div className="response-status">{report ? "HARDWARE STATUS" : "HARDWARE DISCONNECTED"}</div>
    <h2>{report ? report.status : "Waiting for hardware"}</h2>
    <p>{report ? "Status and alerts reported by UN1C0RN^2." : "Connect your Pico to see live readings and hardware alerts."}</p>
    <div className="response-steps">{report?.alert_reasons.length ? report.alert_reasons.map(reason => <div key={reason}><span className="step-pending"/><span>{reason}</span></div>) : <div><span className="step-pending"/><span>{report ? "No hardware alerts reported" : "Alerts: null"}</span></div>}</div>
    <div className="model-score"><span>Isolation Forest score <strong>null</strong></span><small>No model score is available for this hardware report.</small></div>
  </section>;
=======
export default function AiAnalysis() {
  return <section className="response-panel"><div className="response-heading"><span className="sensor-icon"><Icon name="sparkle"/></span><span>UN1C0RN^2 intelligence</span><span className="response-dot"/></div><div className="response-status">AUTOMATED RESPONSE</div><h2>A little heat.<br/>Already on it.</h2><p>A rapid temperature rise was detected at the desk & workstation sensor. Cooling is active and recovery is being verified.</p><div className="response-steps"><div><span className="step-check"><Icon name="check"/></span><span>Cooling fan activated<small>Pico acknowledged the command</small></span></div><div><span className="step-check"><Icon name="check"/></span><span>Fan ramped to 100%<small>Confirmed at the red (76°F) threshold</small></span></div><div><span className="step-pending"/><span>Verifying recovery<small>Temperature easing toward 74°F, fan stepping down to 60%</small></span></div></div><div className="model-score"><span>Isolation Forest score <strong>−0.18</strong></span><small>Safety rule takes priority. Score is not a failure probability.</small></div><Link href="/incidents/1042" className="response-link">View incident #1042 <Icon name="arrow"/></Link></section>;
>>>>>>> 245739c (Last Changes)
}
