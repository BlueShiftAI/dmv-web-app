export default function DisclaimerBanner() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="bg-yellow-50 border-b border-yellow-200 text-yellow-800 text-center text-xs py-1.5 px-4"
    >
      <strong>Educational prototype.</strong> Not affiliated with the SCDMV. Queue,
      appointment, tax, and ownership data are simulated.
    </div>
  );
}
