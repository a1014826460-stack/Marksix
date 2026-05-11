export function formValue(form: HTMLFormElement, name: string) {
  return String(new FormData(form).get(name) || "").trim()
}

export function boolValue(form: HTMLFormElement, name: string) {
  return formValue(form, name) === "1"
}

export function isLongSummaryValue(value: string | number) {
  return String(value).length > 24
}
