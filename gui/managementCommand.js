export async function managementCommand(service, command, payload = {}) {
  const response = await fetch("/management/command", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({service, command, payload})
  });
  if(response.ok && command==="logs" && !response.headers.get("content-type")?.includes("application/json"))
    return {log:await response.text()};
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || value.detail || "요청을 처리할 수 없습니다.");
  return value;
}
