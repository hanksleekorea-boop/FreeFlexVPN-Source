const DELIVERY_STATES = Object.freeze(["none", "issuing", "ready", "downloaded", "imported", "cancelled", "expired", "error"]);
const asTime = value => typeof value === "string" && Number.isFinite(Date.parse(value)) ? new Date(Date.parse(value)).toISOString() : null;

export function evaluateProfileLifecycle(input = {}, options = {}) {
  const now = Date.parse(options.now || new Date().toISOString());
  const deliveryState = DELIVERY_STATES.includes(input.delivery_state) ? input.delivery_state : "none";
  const issuedAt = asTime(input.issued_at), deliveryExpiresAt = asTime(input.delivery_expires_at);
  const existingProfileCount = Number.isInteger(input.existing_profile_count) && input.existing_profile_count >= 0 ? input.existing_profile_count : 0;
  const protectionGrade = ["unconfirmed", "partial", "confirmed"].includes(input.protection_grade) ? input.protection_grade : "unconfirmed";
  if (issuedAt && deliveryExpiresAt && Date.parse(deliveryExpiresAt) <= Date.parse(issuedAt)) throw new Error("DELIVERY_EXPIRY_INVALID");
  const expiredByClock = deliveryExpiresAt && Number.isFinite(now) && now > Date.parse(deliveryExpiresAt);
  let state = "ready_to_issue", nextAction = "issue_isolated_candidate";
  if (deliveryState === "issuing") [state, nextAction] = ["issuing", "wait_without_retry"];
  else if (deliveryState === "error") [state, nextAction] = ["issue_failed", "show_safe_recovery"];
  else if (deliveryState === "cancelled") [state, nextAction] = ["cancelled", "preserve_existing_and_offer_reissue"];
  else if (deliveryState === "expired" || expiredByClock) [state, nextAction] = ["expired", "clear_material_and_offer_reissue"];
  else if (["ready", "downloaded", "imported"].includes(deliveryState) && (!issuedAt || !deliveryExpiresAt)) [state, nextAction] = ["invalid_evidence", "do_not_show_configuration"];
  else if (deliveryState === "ready") [state, nextAction] = ["download_required", "download_once_before_expiry"];
  else if (deliveryState === "downloaded") [state, nextAction] = ["import_required", "import_in_official_wireguard"];
  else if (deliveryState === "imported" && protectionGrade !== "confirmed") [state, nextAction] = ["protection_required", "check_current_candidate_protection"];
  else if (deliveryState === "imported" && input.return_path_confirmed !== true) [state, nextAction] = ["return_path_required", "turn_off_candidate_and_confirm_normal_network"];
  else if (deliveryState === "imported") [state, nextAction] = ["candidate_verified", "legacy_retirement_review_only"];
  return Object.freeze({schema:"FreeFlexVPNProfileLifecycleV1",state,next_action:nextAction,issued_at:issuedAt,delivery_expires_at:deliveryExpiresAt,delivery_material_available:state==="download_required",existing_profile_count:existingProfileCount,existing_profile_action:"preserve",automatic_activation:false,automatic_legacy_revocation:false,contains_configuration:false});
}
