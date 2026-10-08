/** Exercise actual form save functions: hidden outcome values must never be saved as empty. */
import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"
import ts from "typescript"
import { execFileSync } from "node:child_process"

function functionSource(file, name) {
  const source = ts.createSourceFile(file, fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  let match
  function visit(node) {
    if (ts.isFunctionDeclaration(node) && node.name?.text === name) match = node
    ts.forEachChild(node, visit)
  }
  visit(source)
  assert(match, `${file} must expose its real ${name} function`)
  return ts.transpileModule(match.getText(source), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
}

const submitSource = functionSource("features/draws/DrawsPage.tsx", "submit")
for (const [restricted, edited, numbers, expected] of [
  [true, false, "", {}],
  [true, true, "08,09,10,11,12,13,14", { numbers: "08,09,10,11,12,13,14" }],
  [false, false, "01,02,03,04,05,06,07", { numbers: "01,02,03,04,05,06,07" }],
  [false, true, "01,02,03,04,05,06", null],
  [false, true, "01,02,03,04,05,06,06", null],
  [false, true, "01,02,03,04,05,06,50", null],
]) {
  const calls = [], alerts = []
  const scope = {
    editing: { id: 1, numbers: restricted ? "" : numbers, numbers_restricted: restricted },
    numbersEdited: edited, draftYear: "2099", draftTerm: "1", draftNextTerm: "2", draftDrawDate: "2099-01-01",
    draftStatus: "1", draftIsOpened: "0", filteredRows: [], taiwanLottery: { draw_time: "22:32:00" },
    TAIWAN_LOTTERY_ID: 3, Date, FormData: class { get() { return numbers } },
    alert: (value) => alerts.push(value), confirm: () => true,
    normalizeDrawNumbers: (value) => value, parseBeijingDateTime: (value) => new Date(value.replace(" ", "T") + "+08:00"),
    jsonBody: JSON.stringify, adminApi: async (url, options) => calls.push({ url, body: JSON.parse(options.body) }),
    load: async () => [], toast: { success() {} }, setEditing() {}, setFormOpen() {},
  }
  vm.createContext(scope)
  vm.runInContext(submitSource + ";globalThis.save = submit", scope)
  await scope.save({ preventDefault() {}, currentTarget: {} })
  if (expected === null) {
    assert.equal(calls.length, 0, "invalid seven-ball selection must not be submitted")
    assert(alerts.some(message => /7|七/.test(message)), "explain the seven-ball requirement")
    continue
  }
  assert.equal(calls.length, 1, `restricted=${restricted}, edited=${edited}: ${alerts}`)
  assert.deepEqual("numbers" in calls[0].body ? { numbers: calls[0].body.numbers } : {}, expected)
}

const saveEditSource = functionSource("features/site-data/RowEditDialog.tsx", "saveEdit")
for (const intentionalActualEdit of [false, true]) {
  const calls = []
  const editing = { id: 12, content: "candidate", code: "01,02", res_code: "", res_sx: "", result_restricted: true }
  const scope = { editing, editValues: { ...editing, content: "updated", ...(intentionalActualEdit ? { res_code: "14" } : {}) },
    editedFields: new Set(intentionalActualEdit ? ["content", "res_code"] : ["content"]),
    siteId: 7, tableName: "mode_payload_43", source: "public",
    adminApi: async (url, options) => calls.push(JSON.parse(options.body)), onSaved() {}, onError(error) { throw new Error(error) },
  }
  vm.createContext(scope)
  vm.runInContext(saveEditSource + ";globalThis.save = saveEdit", scope)
  await scope.save()
  assert.equal(calls.length, 1)
  assert.equal("res_sx" in calls[0], false, "untouched hidden outcome must be omitted")
  assert.equal("result_restricted" in calls[0], false, "response marker must not become a table write")
  assert.equal(calls[0].content, "updated")
  assert.equal(calls[0].code, "01,02", "candidate numbers retain their normal write behavior")
  if (intentionalActualEdit) assert.equal(calls[0].res_code, "14")
  else assert.equal("res_code" in calls[0], false)
}
{
  const calls = []
  const editing = { id: 12, content: "candidate", result_text: "待开奖", isCorrect: null, is_hit: null,
    draw_is_opened: false, result_balls: [], result_restricted: true }
  const scope = { editing, editValues: { ...editing, content: "updated" }, editedFields: new Set(["content"]),
    siteId: 7, tableName: "mode_payload_43", source: "public",
    adminApi: async (url, options) => calls.push(JSON.parse(options.body)), onSaved() {}, onError(error) { throw new Error(error) },
  }
  vm.createContext(scope)
  vm.runInContext(saveEditSource + ";globalThis.save = saveEdit", scope)
  await scope.save()
  assert.deepEqual(calls, [{ content: "updated" }], "editing candidate content must not overwrite redacted result aliases")
}
// Derive every alias from the real backend redactor, including its context-only
// aliases. Only fields it actually changes at row level must be omitted here.
const hiddenAliases = JSON.parse(execFileSync("python", ["-c", `
import ast, json
from pathlib import Path
from helpers import _hide_public_result_fields
tree = ast.parse(Path("helpers.py").read_text(encoding="utf-8"))
fields = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "_PUBLIC_ACTUAL_RESULT_FIELDS" for target in node.targets))
aliases = set(ast.literal_eval(fields.value.args[0]))
redactor = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_hide_public_result_fields")
for node in ast.walk(redactor):
    if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name) or node.left.id != "key":
        continue
    for value in node.comparators:
        try:
            literal = ast.literal_eval(value)
        except (ValueError, TypeError):
            continue
        if isinstance(literal, str):
            aliases.add(literal)
        elif isinstance(literal, (set, list, tuple)):
            aliases.update(literal)
probe = {key: "original-" + key for key in sorted(aliases)}
probe["raw"] = {"res_code": "14", "content": "candidate"}
hidden = _hide_public_result_fields(probe)
print(json.dumps({key: value for key, value in hidden.items() if value != probe[key]}))
`], { cwd: "src", encoding: "utf8", env: { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", PYTHONDONTWRITEBYTECODE: "1" } }))
for (const intentionalActualEdit of [false, true]) {
  const calls = []
  const editing = { id: 12, ...hiddenAliases, content: "candidate", code: "01,02", result_restricted: true, numbers_restricted: true }
  const intentional = Object.fromEntries(Object.keys(hiddenAliases).map((key) => [key, `intentional-${key}`]))
  const scope = { editing, editValues: { ...editing, content: "updated", ...(intentionalActualEdit ? intentional : {}) },
    editedFields: new Set(["content", "result_restricted", "numbers_restricted", ...(intentionalActualEdit ? Object.keys(hiddenAliases) : [])]),
    siteId: 7, tableName: "mode_payload_43", source: "public",
    adminApi: async (url, options) => calls.push(JSON.parse(options.body)), onSaved() {}, onError(error) { throw new Error(error) },
  }
  vm.createContext(scope)
  vm.runInContext(saveEditSource + ";globalThis.save = saveEdit", scope)
  await scope.save()
  assert.deepEqual(calls, [{ content: "updated", code: "01,02", ...(intentionalActualEdit ? intentional : {}) }],
    `all backend-redacted aliases must ${intentionalActualEdit ? "remain writable when dirty" : "be omitted when untouched"}`)
}
console.log(`restricted result write contract passed (11 real form save scenarios, ${Object.keys(hiddenAliases).length} backend result aliases)`)
