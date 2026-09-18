/**
 * SmartCiti.X : Trade Craft Academy — per-hall practitioner sign-off.
 *
 * v3.4 criterion 1. The pack's honesty block (`pack/manifest.json`'s
 * `honesty.content`) is global: "lesson content is unverified general
 * practice pending authoring by journey-level practitioners." That caveat
 * applies to every hall by default. This module adds the mechanism the
 * roadmap's phrasing ("the per-hall honesty flag") implied but that did not
 * exist anywhere in the tree — a clean-slate addition, not a refinement of
 * something already there.
 *
 * Mirrors `i18n/catalog.mjs`'s reviewer-attribution shape exactly, because
 * it is the same rule at heart: a claim of human sign-off must name who and
 * when, or the build refuses it, and a typo must not be able to invent a
 * fourth state.
 *
 *   i18n/catalog.mjs          -> here
 *   STATUSES                  -> HALL_CONTENT_STATUSES
 *   claimsReview()             -> claimsHallSignoff()
 *   validateCatalog()          -> validateHallContentStatus() / validateHallsContentStatuses()
 *   reviewer / reviewed_at     -> practitioners / signed_off_at
 *
 * A hall record in `pack/registry/halls.json` may carry an optional
 * `content_status` field. Absent means it inherits the global caveat above
 * — so shipping this rule does not itself require touching any of the 111
 * hall records, and none are touched here. A hall claiming
 * "practitioner sign-off" MUST name the practitioner(s) and a date, exactly
 * as a locale catalog claiming "reviewed" must name a reviewer and a date.
 */

/**
 * The closed set of `content_status` values a hall record may declare.
 * Free text here is how a typo becomes a fourth, unnoticed state
 * ("sign off", "signed-off", "reviewed") — every value a hall can carry is
 * named here and nowhere else decides.
 */
export const HALL_CONTENT_STATUSES = Object.freeze([
  // The default this module exists to make explicit and checkable. A hall
  // with no `content_status` at all means exactly the same thing.
  'unverified general practice',
  // A journey-level practitioner is authoring or reviewing this hall's
  // content but has not yet signed off — work in progress, not a claim.
  'pending practitioner authoring',
  // The claim: named practitioner(s), on a named date, signed off this
  // hall's content. The only status this module treats as a review claim.
  'practitioner sign-off',
]);

/**
 * True for the one status that CLAIMS a named human signed off this hall's
 * content. Written as an explicit equality (there is only one claiming
 * status here, unlike i18n's regex match over several "reviewed*" shapes)
 * so that if the closed set above ever grows a second sign-off-ish state,
 * this function has to be revisited rather than silently matching it too.
 */
export function claimsHallSignoff(status) {
  return status === 'practitioner sign-off';
}

/**
 * Validate one hall record's content-status fields. Returns an array of
 * problem strings — empty means clean. Never throws, so a caller can
 * collect every problem across all 111 halls before failing the build.
 *
 * An ABSENT `content_status` is not a problem: it inherits the global
 * caveat, and default-closed here means "still under the caveat", never
 * "silently signed off" — so this function has nothing to validate and
 * returns no problems, which is the honest default per §23.1: a default is
 * a policy decision, and the policy this one encodes is the closed one.
 */
export function validateHallContentStatus(slug, hall) {
  const problems = [];
  const status = hall?.content_status;
  if (status === undefined) return problems;

  if (!HALL_CONTENT_STATUSES.includes(status)) {
    problems.push(`${slug}: content_status ${JSON.stringify(status)} is not one of `
      + `the closed set (${HALL_CONTENT_STATUSES.join(' | ')})`);
    // Still worth checking the practitioner rule below even on an
    // unrecognised status — an invented "signed-off-ish" string must not
    // dodge it just because it also fails the closed-set check.
  }

  if (claimsHallSignoff(status)) {
    const practitioners = hall?.practitioners;
    const names = Array.isArray(practitioners)
      ? practitioners.filter((p) => typeof p === 'string' && p.trim().length > 0)
      : [];
    if (names.length === 0) {
      problems.push(`${slug}: content_status "practitioner sign-off" claims sign-off `
        + 'but names no practitioner');
    }
    const signedOffAt = hall?.signed_off_at;
    if (typeof signedOffAt !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(signedOffAt)) {
      problems.push(`${slug}: content_status "practitioner sign-off" claims sign-off `
        + `but signed_off_at is missing or not an ISO date (got ${JSON.stringify(signedOffAt)})`);
    }
  }
  return problems;
}

/** Validate every hall in a registry's hall list at once. */
export function validateHallsContentStatuses(halls) {
  return halls.flatMap((h) => validateHallContentStatus(h.slug, h));
}
