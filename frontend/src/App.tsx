import FileUploader from "./components/FileUploader";
import StatusTable from "./components/StatusTable";
export default function App() {
  return (
    <div style={{ fontFamily: "system-ui", padding: 24, maxWidth: 900 }}>
      <h1>File Validator</h1>
      <FileUploader />
      <StatusTable />
    </div>
  );
}