export type ToolContract = {
  id: string;
  version: number;
  method: string;
  permissions: string[];
  result_format: string;
  max_result_bytes: number;
  max_findings: number;
  max_observations: number;
};
export type ToolManifest = {
  format: string;
  package_sha256: string;
  checks: ToolContract[];
};
/** UI guidance only; the server performs authoritative approval/execution checks. */
export function toolContractsMatch(
  snapshot: ToolManifest | undefined,
  selected: string[],
  current: ToolManifest | undefined,
): boolean {
  if (
    !snapshot ||
    !current ||
    Object.keys(snapshot).sort().join(",") !== "checks,format,package_sha256" ||
    snapshot.format !== "aegis-tools-v1" ||
    snapshot.format !== current.format ||
    snapshot.package_sha256 !== current.package_sha256 ||
    !Array.isArray(snapshot.checks) ||
    !Array.isArray(current.checks) ||
    snapshot.checks.length !== selected.length ||
    !selected.length ||
    new Set(selected).size !== selected.length
  )
    return false;
  return selected.every((id, index) => {
    const saved = snapshot.checks[index];
    const active = current.checks.find((check) => check?.id === id);
    return (
      saved?.id === id &&
      !!active &&
      JSON.stringify(saved, Object.keys(saved).sort()) ===
        JSON.stringify(active, Object.keys(active).sort())
    );
  });
}
