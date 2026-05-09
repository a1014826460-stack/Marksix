/**
 * API 测试快捷启动脚本
 *
 * 用法：
 *   node test/run-api-test.js
 *   node test/run-api-test.js http://127.0.0.1:3000
 *
 * 此脚本自动检测 tsx / ts-node 并执行 TypeScript 测试文件。
 */

const { execSync } = require("child_process");

const baseUrl = process.argv[2] || "http://127.0.0.1:3000";

function has(cmd) {
  try {
    execSync(`${cmd} --version`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

let runner = null;

if (has("npx tsx")) {
  runner = "npx tsx";
} else if (has("npx ts-node")) {
  runner = "npx ts-node --project tsconfig.json";
} else {
  console.error("请安装 tsx: npm install -D tsx");
  console.error("或安装 ts-node: npm install -D ts-node");
  process.exit(1);
}

const cmd = `${runner} test/api-test.ts --base-url=${baseUrl}`;
console.log(`执行: ${cmd}\n`);

try {
  execSync(cmd, { stdio: "inherit", cwd: require("path").dirname(__dirname) });
} catch (e) {
  process.exit(e.status || 1);
}
