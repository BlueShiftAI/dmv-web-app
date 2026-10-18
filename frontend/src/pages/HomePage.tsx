import { Link } from "react-router-dom";

const steps = [
  { n: "1", title: "Describe your situation", desc: "Answer a few questions about your vehicle purchase." },
  { n: "2", title: "Get your checklist", desc: "Receive the exact documents and forms required for your scenario." },
  { n: "3", title: "Prepare your documents", desc: "Upload sample photos and fill out your form draft." },
  { n: "4", title: "Check tax & ownership status", desc: "Run simulated lookups before your visit." },
  { n: "5", title: "Book an appointment", desc: "Reserve a demo time slot and see live queue estimates." },
  { n: "6", title: "Check in & track your turn", desc: "Receive an in-app alert when you are called." },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="text-center py-12">
        <h1 className="text-3xl font-bold text-brand-900 mb-4">
          Prepare for Your DMV Visit
        </h1>
        <p className="text-gray-600 max-w-2xl mx-auto mb-8">
          This tool helps you prepare for a private-party vehicle registration at the
          Rock Hill, SC DMV office. Complete the preparation checklist, upload sample
          documents, and track simulated wait times — all before you arrive.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link to="/register" className="btn-primary px-6 py-3 text-base">
            Start Preparation
          </Link>
          <Link to="/login" className="btn-secondary px-6 py-3 text-base">
            Sign In
          </Link>
        </div>
      </section>

      <section aria-labelledby="steps-heading">
        <h2 id="steps-heading" className="text-center text-xl font-semibold mb-6">
          How It Works
        </h2>
        <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {steps.map((s) => (
            <li key={s.n} className="card flex gap-4">
              <span
                className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white
                           flex items-center justify-center font-bold text-sm"
                aria-hidden="true"
              >
                {s.n}
              </span>
              <div>
                <h3 className="font-semibold text-sm mb-1">{s.title}</h3>
                <p className="text-sm text-gray-600">{s.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="card bg-blue-50 border-blue-200">
        <h2 className="text-base font-semibold text-blue-900 mb-2">
          Supported Scenario
        </h2>
        <p className="text-sm text-blue-800">
          This demo covers <strong>registering a previously-titled South Carolina vehicle
          purchased from a private seller</strong> in York County, SC.
          Out-of-state titles, dealer sales, commercial vehicles, motorcycles, and
          REAL ID are not supported. Unsupported cases will be directed to
          <a href="https://www.scdmvonline.com" className="underline ml-1" target="_blank" rel="noopener noreferrer">
            scdmvonline.com
          </a>.
        </p>
      </section>
    </div>
  );
}
