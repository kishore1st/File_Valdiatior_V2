// k6 load test: concurrent uploads
import http from "k6/http";
import { check } from "k6";
import { FormData } from "https://jslib.k6.io/formdata/0.0.2/index.js";

export const options = {
  scenarios: {
    upload_50u: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 50 },
        { duration: "2m",  target: 50 },
        { duration: "30s", target: 0  },
      ],
    },
  },
};

const BASE = __ENV.FVI_API || "http://localhost:8000";
const TOKEN = __ENV.FVI_TOKEN || "okta-uploader";

export default function () {
  const csv = `customer_id,first_name,last_name,dob,country\n${__VU},T,User,1990-01-01,IN\n`;
  const fd = new FormData();
  fd.append("schema_type_key", "customer");
  fd.append("region_code", "IN");
  fd.append("files", http.file(csv, `vu${__VU}_${Date.now()}.csv`, "text/csv"));

  const res = http.post(`${BASE}/v1/batches`, fd.body(), {
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": `multipart/form-data; boundary=${fd.boundary}` },
  });
  check(res, { "202/200": (r) => r.status === 200 || r.status === 202 });
}