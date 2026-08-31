/** Retired GEM extraction prototype using the development-only artifact tool. */
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


const root = fileURLToPath(new URL("../../", import.meta.url));
const input = `${root}data/raw/gem/LNG-Carrier-Tracker-December-2025-release.xlsx`;
const output = `${root}data/interim/gem_lng_carriers.json`;
const metadataOutput = `${root}data/interim/gem_lng_carriers_metadata.json`;

const blob = await FileBlob.load(input);
const workbook = await SpreadsheetFile.importXlsx(blob);
const sheet = workbook.worksheets.getItem("data");
const values = sheet.getRange("A1:AG1144").values;
const headers = values[0].map(String);
const records = values.slice(1)
  .filter((row) => row[0] !== null && row[0] !== "")
  .map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index]])));

const sourceBytes = await fs.readFile(input);
await fs.mkdir(`${root}data/interim`, { recursive: true });
await fs.writeFile(output, `${JSON.stringify(records, null, 2)}\n`);
await fs.writeFile(metadataOutput, `${JSON.stringify({
  source_file: "data/raw/gem/LNG-Carrier-Tracker-December-2025-release.xlsx",
  source_sha256: createHash("sha256").update(sourceBytes).digest("hex"),
  source_sheet: "data",
  extracted_rows: records.length,
  extracted_columns: headers,
  extraction_tool: "@oai/artifact-tool",
}, null, 2)}\n`);

console.log(`wrote ${output}`);
console.log(`rows=${records.length} columns=${headers.length}`);
