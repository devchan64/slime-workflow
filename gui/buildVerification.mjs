export function isBuildVerificationFresh(verification,now=Date.now()){
  return Boolean(verification && verification.record?.status==='rebuild_required' &&
    Number.isFinite(verification.checkedAt) && now>=verification.checkedAt && now-verification.checkedAt<30000);
}
