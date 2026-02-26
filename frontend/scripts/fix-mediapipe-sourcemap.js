const fs = require("fs");
const path = require("path");

const mapPath = path.join(
  __dirname,
  "..",
  "node_modules",
  "@mediapipe",
  "tasks-vision",
  "vision_bundle_mjs.js.map"
);

const minimalMap = JSON.stringify({
  version: 3,
  file: "vision_bundle.mjs",
  sources: [],
  names: [],
  mappings: "",
});

try {
  if (!fs.existsSync(mapPath)) {
    fs.mkdirSync(path.dirname(mapPath), { recursive: true });
    fs.writeFileSync(mapPath, minimalMap, "utf8");
    console.log("[postinstall] Created stub sourcemap for @mediapipe/tasks-vision.");
  }
} catch (error) {
  console.warn("[postinstall] Unable to patch @mediapipe/tasks-vision sourcemap:", error.message);
}
