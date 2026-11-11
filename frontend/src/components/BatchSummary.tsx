export default function BatchSummary({ summary }: { summary: any }) {
  if (!summary) return null;
  return (
    <div>
      <h4>Batch {summary.batch_id}</h4>
      <ul>
        <li>Total: {summary.total_files}</li>
        <li>Succeeded: {summary.succeeded}</li>
        <li>Duplicates: {summary.duplicates}</li>
        <li>Validation failed: {summary.validation_failed}</li>
        <li>Processing failed: {summary.processing_failed}</li>
        <li>In progress: {summary.in_progress}</li>
      </ul>
    </div>
  );
}