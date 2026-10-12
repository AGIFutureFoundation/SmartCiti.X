/**
 * ACP-11 Plane 2 — the mentor agent contract and the middleware every mentor
 * runs behind. Framework-agnostic: LangChain/LangGraph wiring adapts to this,
 * not the other way round, so the guards are testable without an LLM call.
 *
 * The load-bearing rule (ACP-09): mentors are READ-ONLY consumers of control
 * state. They voice the system; they never steer it. That is enforced here in
 * code rather than asked for in a prompt.
 */

/** Control-plane surfaces a mentor may read. Anything else is out of scope. */
export const READ_SCOPES = Object.freeze([
  'profile.summary', 'dial.state', 'module.content', 'hint.ladder', 'skill.graph',
]);

/** Actions no mentor may ever take, whatever it is asked. */
export const FORBIDDEN_ACTIONS = Object.freeze([
  'dial.set_setpoint', 'dial.pin', 'profile.write', 'gate.certify',
  'profile.read_other_learner', 'registry.write', 'override.apply',
]);

export class ScopeViolation extends Error {
  constructor(action) {
    super(`scope: mentors may not perform "${action}"`);
    this.name = 'ScopeViolation';
    this.action = action;
  }
}

/* ------------------------------------------------------------------ PII ---- */
// Order matters: the most specific, labelled identifiers run first so a looser
// pattern later (phone, card) never half-eats them. Every replacement token is
// digit-free, so no pattern can re-match an earlier replacement. Labels ("DOB",
// "licence number is") are kept so the mentor still knows WHAT was shared.
const ID_TOKEN = String.raw`(?:[A-Z]{1,4}[ -])?(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{3,}[A-Z0-9]`;
const DATE = String.raw`(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})`;
const DOB_LABEL = String.raw`(?:[Dd]\.?[Oo]\.?[Bb]\.?|[Dd]ate of [Bb]irth|[Bb]irth ?[Dd]ate|[Bb]orn(?: on)?|[Bb]irthday)`;
const NAME = String.raw`[A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+){1,2}`;
const keepLabel = (tag) => (_m, label) => `${label}[redacted-${tag}]`;
const PII_PATTERNS = [
  [/\b\d{3}-\d{2}-\d{4}\b/g, '[redacted-id]'],
  [/\b((?:SSN|social security(?: number| no\.?)?)\s*(?:#|number|no\.?)?\s*(?:is|was|:)?\s*)\d{9}\b/gi, keepLabel('id')],
  [/\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b/g, '[redacted-email]'],
  [/\b(?:\d[ -]?){13,16}\b/g, '[redacted-card]'],
  // health-plan / member identifiers: Medicaid, Medicare, insurance, MRN
  [new RegExp(String.raw`\b((?:medicaid|medicare|insurance|member|policy|patient|MRN|health ?plan)\s*(?:id|number|num|no\.?|#)?\s*(?:#|is|was|:|=)?\s*)${ID_TOKEN}\b`, 'gi'), keepLabel('health-id')],
  // licence / permit / card / ID numbers: only when labelled AND containing a digit
  [new RegExp(String.raw`\b((?:driver'?s?\s+licen[cs]e|DL|licen[cs]e|lic\.?|permit|card|cert(?:ificate)?|badge|state ?ID|ID)\s*(?:number|num|no\.?|#|id)?\s*(?:#|is|was|:|=)?\s*)${ID_TOKEN}\b`, 'gi'), keepLabel('licence')],
  // a name sitting next to a date of birth is identifying as a pair
  [new RegExp(String.raw`\b${NAME}(?=\s*[,(-]?\s*(?:(?:was|is)\s+)?${DOB_LABEL}\b)`, 'g'), '[redacted-name]'],
  [new RegExp(String.raw`\b(${DOB_LABEL}\s*(?:is|was|:|-)?\s*)${DATE}`, 'gi'), keepLabel('dob')],
  [new RegExp(String.raw`(\[redacted-dob\][,;]?\s*(?:for|of|-|is)?\s*)${NAME}`, 'g'), (_m, l) => `${l}[redacted-name]`],
  [/\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b/g, '[redacted-phone]'],
  [/\b\d{1,5}\s+[A-Z][a-z]+\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Ln)\b/g, '[redacted-address]'],
];

export function redactPII(text) {
  if (typeof text !== 'string') return text;
  let out = text, hits = 0;
  for (const [re, rep] of PII_PATTERNS) {
    out = out.replace(re, (...a) => { hits++; return typeof rep === 'function' ? rep(...a) : rep; });
  }
  return { text: out, redactions: hits };
}

/* ----------------------------------------------------------- escalation ---- */
/*
 * Each trigger names its category, the human route it hands to, and why. The
 * mentor never answers these on its own authority: the middleware flags the
 * turn and the route decides who picks it up. Order is priority — crisis first,
 * so a message that is both a crisis and anything else goes to the crisis desk.
 *
 * Patterns are scoped to the REQUEST, not the vocabulary: "patch test",
 * "lock-out tag colours", "developer volume", "colour bleeding into foils" are
 * technique and must stay quiet (fixtures in mentor_scope_fixtures.json prove it).
 */
const DRUG = String.raw`(?:isotretinoin|accutane|tretinoin|retin-?a|minoxidil|rogaine|finasteride|spironolactone|lidocaine|benzocaine|numbing (?:shot|injection)|benadryl|diphenhydramine|antihistamine|zyrtec|claritin|ibuprofen|advil|motrin|tylenol|acetaminophen|aspirin|prednisone|steroids?|cortisone|hydrocortisone|antibiotics?|antifungals?|terbinafine|lamisil|fluconazole|diflucan|doxycycline|minocycline|amoxicillin|clindamycin|cephalexin|neosporin|bacitracin|botox|filler|opioids?|oxy\w*|xanax|valium|adderall|metformin|insulin|epipen|epinephrine)`;
const PILL = String.raw`(?:pills?|tablets?|capsules?|meds|medications?|medicine|milligrams?|mg\b|mcg\b|shots?|injections?)`;
const ASK = String.raw`(?:can|could|may|should|do|would|will)\s+(?:i|we|you|u)\b|\b(?:we|i)\s+can\s+just\b|\bright\s*\?|how\s+(?:do|can|could|would|should)\s+(?:i|we)\b|is\s+it\s+(?:ok|okay|fine|alright|safe|cool)|so\s+(?:that\s+)?(?:i|we)\s+(?:can|could|don'?t)|just\s+this\s+once|i'?m\s+(?:going|gonna)\s+to|let\s+me|i\s+(?:want|need)\s+to|\bwithout\b|\banyway\b|\binstead\b`;
const re = (s, f = 'i') => new RegExp(s, f);

const LEGAL = re(String.raw`\b(?:damages|compensation|liab(?:le|ility)|small\s+claims|chargeback)\b[^.?!]{0,60}\b(?:do\s+i\s+have\s+to|must\s+i|am\s+i|should\s+i|pay)|\b(?:do\s+i\s+have\s+to|must\s+i)\s+(?:pay|refund)\b[^.?!]{0,40}\b(?:damages|compensation)|\b(?:(?:don'?t|dont|do\s+not)\s+have|without|no)\s+(?:my\s+|any\s+|legal\s+)?papers\b|\bundocumented\b|\b(?:my|her|his|their)\s+(?:immigration\s+|visa\s+|legal\s+)?status\s+(?:runs?\s+out|ran\s+out|expir\w*|ends?|lapse\w*)|\boverstay\w*|\b(?:i'?m|i\s+am|me|us|we'?re)\s+(?:an?\s+)?(?:independent\s+)?contractors?\b[^.?!]{0,80}\b(?:but|sets?|takes?|can\s+(?:she|he|they))|\b(?:boss|owner|manager|employer)\b[^?]{0,80}\bcan\s+(?:she|he|they)\s+(?:do\s+that|legally|make\s+me|fire\s+me|keep|take)|\b(?:visa)\b(?!\s*(?:card|debit|credit|gift))|\bimmigra\w*|\bgreen\s+card\b|(?<!(?:hot|energi[sz]ed|electrical|confined[-\s]space|entry|building)\s)\bwork\s+permit\b|\bcitizenship\b|\bdeport\w*|\bundocumented\b|\basylum\b|\bDACA\b|\bITIN\b|\bI-9\b|\bE-?Verify\b|\b(?:sue|sued|suing|lawsuit|lawyer|attorney|legal\s+action|small\s+claims|subpoena|malpractice|settlement)\b|\bunder\s+the\s+table\b|\boff\s+the\s+books\b|\bis\s+(?:that|this|it)\s+(?:even\s+)?(?:legal|illegal|allowed\s+by\s+law)\b|\billegal\w*|\b(?:labor|labour)\s+(?:law|board|department)\b|\bwage\s+theft\b|\bkeep(?:s|ing)?\s+(?:all\s+)?my\s+tips\b|\bminimum\s+wage\b|\bmisclassif\w*|\bworkers'?\s+comp\w*|\b(?:sign|break|breach|enforce)\w*\s+(?:a\s+|the\s+|my\s+|this\s+)?(?:\w+\s+)?(?:contract|lease|non-?compete|nda)\b|\bwithout\s+(?:a\s+|my\s+)?licen[cs]e\b|\bunlicensed\b`);

const ESCALATION_TRIGGERS = [
  {
    id: 'crisis', category: 'crisis', route: 'human_crisis',
    reason: 'possible self-harm or crisis: hand to a human now, with crisis resources',
    re: re(String.raw`\b(?:kill(?:ing|in'?)?\s+my\s*self|(?:rather|better)\s+(?:be\s+)?dead|(?:wrote|writing|written|left|leaving)\s+(?:\w+\s+)?(?:goodbye|suicide|farewell)\s+(?:letters?|notes?|messages?)|giv(?:e|ing)\s+away\s+(?:all\s+)?my\s+(?:stuff|things|kit|tools|belongings)|saying\s+(?:my\s+)?goodbyes?|(?:don'?t|dont|can'?t|cant)\s+see\s+(?:the\s+|a\s+|any\s+)?point\s+(?:in|of|to)\s+(?:waking|living|going\s+on|being\s+(?:alive|here)|life|anything|carrying\s+on)|(?:want|wanna)\s+(?:to\s+)?disappear|disappear\s+forever|(?:never|not)\s+wake\s+up\s+(?:again|tomorrow)?|sleep\s+forever|suicid\w*|unalive|\bkms\b|end(?:ing)?\s+it\s+all|can'?t\s+go\s+on|(?:end|ending|take|taking)\s+my\s+(?:own\s+)?life|(?:want|wanna|wanted|going|gonna|ready|deserve)\s+(?:to\s+|2\s+)die\b(?!\s*(?:grinder|cast|set|stock|head|plate))|(?:don'?t|do\s+not|dont)\s+(?:even\s+)?(?:want|wanna)\s+(?:to\s+)?(?:be\s+alive|live|exist|wake\s+up|be\s+here)|wish\s+i\s+(?:was|were|wasn'?t)\s+(?:dead|alive|here|born)|(?:hurt|hurting|harm|harming|cut|cutting|burn|burning|starv\w*)\s+my\s*self(?![^.?!]{0,30}\b(?:accident\w*|by\s+mistake|with\s+(?:the|my|a)\s+(?:shears|scissors|razor|blade|clippers|knife|file|drill)|on\s+(?:the|a)\s))|self[-\s]?harm\w*|(?:saving|saved|stockpil\w*|hoard\w*|collect\w*)\s+(?:up\s+)?(?:all\s+)?(?:my\s+|some\s+|the\s+)?(?:pills|meds|tablets|medication)|(?:take|took|swallow\w*)\s+(?:all|every|a\s+bunch\s+of|the\s+whole\s+bottle\s+of)\s+(?:my\s+|the\s+)?(?:pills|meds|tablets)|overdos\w*|better\s+off\s+without\s+me|(?:nobody|no\s+one|noone)\s+(?:would|will|is\s+gonna|is\s+going\s+to)\s+miss\s+me|no\s+(?:point|reason)\s+(?:anymore|in\s+living|to\s+live|living)|nothing\s+to\s+live\s+for|not\s+safe\s+at\s+home)`),
  },
  {
    id: 'safety_incident', category: 'safety_incident', route: 'human_instructor_now',
    reason: 'an injury or emergency is happening: a human instructor or emergency services, not a mentor',
    test: (t) => {
      const PREVENT = /\b(?:avoid\w*|prevent\w*|reduc\w*|minimi[sz]\w*|protect\w*|without|risk\s+of|chance\s+of|so\s+(?:i|we|they|she|he)\s+(?:don'?t|do\s+not)|don'?t\s+get|safe\s+from|stop\s+(?:a|an))\b/i;
      for (const s of t.split(/[.?!;]+/)) {
        if (re(String.raw`\b(?:injur|electrocut)\w*`).test(s) && !PREVENT.test(s)) return true;
      }
      if (re(String.raw`\bfell\s+(?:from|off)\b|\bunconscious\b|\bambulance\b|\bpassed\s+out\b|\bnot\s+breathing\b|\bseizure\b|\bchemical\s+burn\b|\b(?:got|been|was|is)\s+(?:badly\s+)?(?:burned|burnt|shocked)\b|\bcut\s+(?:myself|my\s+(?:finger|hand|thumb))\b[^.?!]{0,40}\b(?:shears|scissors|razor|blade|clippers|knife|accident\w*)`).test(t)) return true;
      // "What do I do IF a client starts bleeding" is a first-aid procedure
      // question (taught content); a present-tense report still escalates.
      // "bleeding" is a colour term of art; it is an incident only with an
      // injury beside it and no colour vocabulary in the same sentence.
      for (const s of t.split(/[.?!;]+/)) {
        if (!/\bbl(?:eed|ed)\w*/i.test(s)) continue;
        const strong = /\b(?:blood\w*|wound\w*|injur\w*|gash\w*|lacerat\w*|stitch\w*|first\s+aid|won'?t\s+stop)\b/i.test(s);
        const colour = /\b(?:colou?r\w*|toner|foils?|dye\w*|tint\w*|pigment\w*|ink|lighten\w*|highlight\w*|balayage|gloss\w*|shade\w*|red|blonde|brunette|copper|level\s+\d)\b|\bbleach\w*/i.test(s);
        const injury = /\b(?:nick\w*|cut|cuts|sliced|finger|thumb|hand|ear|arm|leg|face|neck|lip|nose)\b/i.test(s);
        const hypothetical = /\b(?:what\s+(?:do|should)\s+(?:i|we|you)\s+do|how\s+(?:do|should)\s+(?:i|we|you)\s+(?:handle|treat|respond|disinfect|clean\s+up|clean|sanitize|dispose))\b[^.?!]{0,20}\b(?:if|when|after)\b/i.test(s) && !/\b(?:is|are|was|keeps?|won'?t\s+stop|right\s+now|just)\s+(?:still\s+)?bl/i.test(s);
        if ((strong || (injury && !colour)) && !hypothetical) return true;
      }
      return false;
    },
  },
  {
    id: 'credential_fraud', category: 'certify', route: 'human_registrar',
    reason: 'only a licensed instructor or the state board can sign off hours, competencies or credentials',
    re: re(String.raw`\b(?:fake|faked|forge[ds]?|forging|counterfeit|falsif\w*|photoshop\w*|doctor(?:ed)?|backdat\w*)\s+(?:\w+\s+){0,3}(?:cert\w*|licen[cs]\w*|ticket|card|diploma|credential\w*|hours?|log|transcript|signature|record)|\b(?:cert\w*|licen[cs]e|card|diploma|credential|ticket|hours?)\s+(?:\w+\s+){0,4}(?:faked|forged|fake|counterfeit|falsified|photoshopped)\b|\b(?:buy|purchase|pay\s+for|order)\s+(?:a\s+|an\s+|my\s+)?(?:\w+\s+){0,3}(?:cert\w*|licen[cs]e|card|diploma|credential|hours)|\b(?:get|obtain)\s+(?:a\s+|an\s+|my\s+)?(?:\w+\s+){0,3}(?:licen[cs]e|cert\w*|card)\s+(?:without|w\/o)\s+(?:doing\s+|taking\s+)?(?:the\s+)?(?:hours|exam|test|school|training)|\b(?:cert\w*|licen[cs]e|card|diploma|credential)\s+(?:\w+\s+){0,3}(?:buy|purchase|order|get|pay\s+for)\b[^.?!]{0,30}\b(?:online|without)|\b(?:licen[cs]e|cert\w*|card|diploma)\b[^.?!]{0,60}\bwithout\s+(?:doing\s+|taking\s+|finishing\s+|completing\s+|going\s+to\s+)?(?:the\s+|my\s+|any\s+)?(?:hours|apprenticeship|exam|test|school|training|classes)|\b(?:tick|check|mark|fill\s+(?:in|out)|put\s+down|write\s+down|say|state)\b[^.?!]{0,40}\b(?:saying|that\s+says|to\s+say|showing|that)\s+(?:that\s+)?i\s+(?:completed|passed|finished|did|have\s+(?:done|completed|finished)|am\s+(?:trained|certified|licensed|competent))|(?:(?:can|could|would|will)\s+(?:you|u|ya)|please|pls|plz|just)\s+(?:please\s+|just\s+)?(?:sign|log|mark|record|add|enter|put\s+down|put|certify|approve|verify|pass|vouch|initial|credit)\b[^.?!]{0,50}\b(?:hours?|hrs|hour\s+sheet|timesheet|time\s+sheet|log\s*book|competenc\w*|passed|certif\w*|licen[cs]\w*|record|transcript|check-?off|apprenticeship)|\b(?:take|sit|write|do)\s+(?:the\s+|my\s+)?(?:\w+\s+){0,3}(?:exam|test|board|written|practical|quiz)\s+for\s+me\b|\b(?:put|mark|sign|count|list)\s+(?:me|him|her|them)\s+(?:down\s+)?(?:as\s+)?(?:present|attended|in\s+attendance)\b[^.?!]{0,60}\b(?:wasn'?t|was\s+not|weren'?t|didn'?t|never|even\s+though|absent)|\bmark\s+(?:me|him|her|them|my\s+\w+)\s+(?:as\s+)?(?:passed|complete[d]?|competent|certified|present|signed\s+off)|\bsign\s+(?:off\s+)?(?:on\s+)?my\s+(?:\w+\s+){0,3}(?:hours|hour\s+sheet|timesheet)\b[^.?!]{0,30}\b(?:as\s+my|for\s+me)|\bas\s+my\s+(?:supervising|supervisor|sponsor\w*|instructor|licensee)|\bhours?\s+(?:that\s+)?i\s+(?:didn'?t|did\s+not|never|dont|don'?t)\s+(?:do|work|attend|have)|\b(?:log|add|record|enter|count|credit)\b[^.?!]{0,40}\bhours?\b[^.?!]{0,40}\b(?:at\s+home|didn'?t|did\s+not|never|wasn'?t\s+there|off\s+the\s+books)|\b(?:write|make|print|create|generate|issue|draft)\s+(?:me\s+)?(?:a\s+|an\s+)?(?:\w+\s+){0,2}(?:certificat\w*|diploma|licen[cs]e|card|letter)\s+(?:\w+\s+){0,2}(?:saying|stating|that\s+says|showing|proving)`),
  },
  {
    id: 'chemical_bypass', category: 'chemical_bypass', route: 'human_instructor',
    reason: 'defeating a label, SDS, test or safety device is never mentor advice',
    test: (t) => {
      const DEVICE = String.raw`(?:interlock\w*|safety\s+(?:switch|guard|cut-?off|sensor)|guard\w*|lock-?out\w*|tag-?out|lock\s+and\s+tag|LOTO|gas\s+(?:detector|monitor|alarm|sensor)|co2?\s+(?:detector|alarm|monitor)|smoke\s+(?:detector|alarm)|e-?stop|emergency\s+stop|kill\s+switch|gfci|fire\s+alarm|sprinkler|dead-?man)`;
      const DET = String.raw`(?:(?:out|off|the|a|an|its|my\s+own|his|her|their|someone(?:\s+else)?'?s|another\s+\w+'?s|supervisor'?s|this|that)\s+)*(?:[\w-]+\s+){0,2}`;
      // strong verbs are a bypass whatever the framing
      if (re(String.raw`\b(?:bypass\w*|defeat\w*|override|disabl\w*|jumper\w*(?:\s+out)?|jump\s+out|tape\s+(?:down|over)|wedge\w*|tie\s+(?:back|off)|silenc\w*|mute|cheat\w*)\s+${DET}${DEVICE}`).test(t)) return true;
      // weak verbs (remove, cut, take off...) only when the learner is asking to do it
      const weak = re(String.raw`\b(?:remove|cut|pull|unplug\w*|turn\w*\s+off|shut\w*\s+off|switch\w*\s+off|take|taking)\s+${DET}${DEVICE}|\btake\s+(?:the\s+|a\s+)?(?:[\w-]+\s+){0,2}(?:guard|interlock|lock|tag)\s+off\b|\b(?:cut|pull|take)\s+(?:my\s+own\s+|the\s+|his\s+|their\s+)?(?:lock-?out\s+)?(?:lock|tag)\s+off\b`);
      if (weak.test(t) && re(ASK).test(t) && !/\bwho\s+(?:is|'?s)\s+(?:allowed|authori[sz]ed|permitted)/i.test(t)) return true;
      if (re(String.raw`\b(?:gas|co2?|smoke|h2s|oxygen|o2|fire)\s+(?:detector|monitor|alarm|sensor|meter)\b[^.?!]{0,80}\b(?:shut\s+it\s+(?:up|off)|turn\s+it\s+off|make\s+it\s+stop|stop\s+it\s+(?:beeping|going\s+off)|silence\s+it|mute\s+it|disable\s+it|unplug\s+it|ignore\s+it|take\s+the\s+batter(?:y|ies)\s+out)`).test(t)) return true;
      if (re(String.raw`\b(?:skip\w*|bypass\w*|ignore|forget(?:\s+about)?|ditch|blow\s+off|no|without|not\s+bother\s+(?:with|doing)|not\s+(?:do|need)|(?:don'?t|dont)\s+(?:need|have\s+to\s+do|bother\s+with)|no\s+need\s+for|get\s+away\s+without|pass\s+on)\s+(?:the\s+|a\s+|doing\s+(?:the\s+|a\s+)?|any\s+)?(?:patch|strand|allergy|sensitivity|predisposition|skin|spot)?\s*test\w*\b|\bwithout\s+(?:\w+\s+){0,2}test(?:ing)?\b`).test(t) && re(ASK).test(t)) return true;
      if (re(String.raw`\b(?:sds|msds|label|manufacturer|instructions|directions|warning)\b[^.?!]{0,30}\b(?:says?|said|warns?|recommends?)\b[^.?!]{0,20}\b(?:not|n'?t|never|no)\b[^?]{0,80}\b(?:but|anyway|still|can\s+i|could\s+i)\b`).test(t)) return true;
      if (re(String.raw`\b(?:longer|stronger|hotter|higher|more|past)\s+than\s+(?:what\s+)?(?:the\s+)?(?:label|sds|manufacturer|directions|instructions|bottle|processing\s+time)`).test(t) && re(ASK).test(t)) return true;
      if (re(String.raw`\b(?:label|bottle|sds|manufacturer|instructions|directions)\s+(?:says?|said|states?)\s+(?:max(?:imum)?|no\s+(?:more|longer)\s+than|up\s+to|only)\b[^.?!]{0,40}\b(?:but|who\s+checks|anyway|whatever)\b`).test(t)) return true;
      if (re(String.raw`\b(?:work|working|do\s+it|stay)\s+(?:on\s+)?(?:[\w-]+\s+){0,2}(?:live|hot|energi[sz]ed)\b[^.?!]{0,40}\b(?:instead\s+of|rather\s+than|without|so\s+i\s+don'?t\s+have\s+to)\b[^.?!]{0,30}\b(?:lock\w*|tag\w*|LOTO|de-?energi[sz]\w*|shut\w*\s+(?:it\s+)?off)`).test(t)) return true;
      if (re(String.raw`\b(?:against|despite|ignor\w*|regardless\s+of)\s+(?:what\s+)?(?:the\s+)?(?:sds|msds|label|manufacturer|instructions|directions|warning)`).test(t)) return true;
      if (re(String.raw`\b(?:bleach|chlorine|hypochlorite)\b[^.?!]{0,40}\bammonia\b|\bammonia\b[^.?!]{0,40}\b(?:bleach|chlorine)\b`).test(t) && re(ASK).test(t) && !/\b(?:why|explain)\b/i.test(t)) return true;
      if (re(String.raw`\b(?:MMA|methyl\s+methacrylate)\b`).test(t) && re(String.raw`\b(?:mix|add|use|using|put|buy|cheaper|swap|instead)\b`).test(t)) return true;
      if (re(String.raw`\b(?:relaxer|hydroxide|lye|no-?lye|perm|thio\w*)\b[^.?!]{0,50}\b(?:bleach\w*|lightened|highlight\w*|lifted)\b[^.?!]{0,40}\bsame\s+day|\bsigns?\s+a\s+waiver\b|\bwaiver\s+so\s+(?:i|we)\s+can\b`).test(t)) return true;
      if (re(String.raw`\b(?:ventilation|vent|fan|extractor|exhaust|respirator|fume\s+(?:hood|extractor))\b[^.?!]{0,25}\b(?:broken|down|off|not\s+working|out|dead|dont\s+work|doesn'?t\s+work)|\bwithout\s+(?:a\s+|any\s+|the\s+)?(?:ventilation|respirator|exhaust)|\bclosed\s+(?:back\s+)?room\b`).test(t) && re(ASK).test(t)) return true;
      return false;
    },
  },
  {
    id: 'dosing', category: 'dosing', route: 'human_medical_referral',
    reason: 'medication and dosing are for a physician or pharmacist, never a mentor',
    re: re(String.raw`\b(?:inject\w*|prescri\w*)\b|\b(?:double|triple|halve|increase|decrease|lower|raise|up|cut|skip|stop)\s+(?:her|his|my|their|the)\s+(?:dose|dosage|meds|medication|pills|${DRUG})|\bby\s+mouth\b|\boral\s+(?:antibiotic|antifungal|medication|steroid|minoxidil|retinoid)|\b\d+(?:\.\d+)?\s?(?:mg|mcg|milligrams?)\b|\b(?:how\s+(?:many|much)|what\s+(?:dose|dosage|strength|amount)|which\s+(?:dose|dosage|strength)|dosage\s+of|dose\s+of)\b[^.?!]{0,60}\b(?:${DRUG}|${PILL})|\b${DRUG}\b[^.?!]{0,60}\b(?:dose|dosage|doses|how\s+much|how\s+many|take|taking|give|giving|start\s+(?:on|at)|strength|mg)\b|\b(?:rub|dab|spread|smear|put|apply|use|recommend|give)\s+(?:some\s+|a\s+little\s+|a\s+bit\s+of\s+|a\s+|an\s+)?(?:hydrocortisone|cortisone|steroid\s+cream|neosporin|bacitracin|antibiotic\s+(?:cream|ointment)|lidocaine|benzocaine|lamisil|terbinafine|clotrimazole|ketoconazole|tretinoin|retin-?a)\b|\b(?:put|apply|use|recommend|give|tell\s+(?:her|him|them)\s+to\s+use)\s+(?:some\s+|a\s+|an\s+)?(?:\w+\s+)?(?:steroid|cortisone|hydrocortisone|antibiotic|antifungal|prescription|numbing)\s+(?:cream|ointment|gel|lotion|pills?)`),
  },
  {
    id: 'medical_dx', category: 'medical_dx', route: 'human_medical_referral',
    reason: 'naming a disease or infection is a diagnosis: refer the client to a physician',
    re: re(String.raw`(?<!(?:can'?t|cannot|not|never|won'?t|shouldn'?t|don'?t)\s+)\bdiagnos\w*|\b(?:sores?|rash|lesions?|bumps?|lumps?|patch(?:es|y)?|spots?|growths?|crust\w*|scabs?|blisters?|swell\w*|pus|discharge|hair\s+loss|bald\w*|discolou?r\w*|green|yellow\w*)\b[^.?!]{0,80}\b(?:look(?:s|ing)?\s+like\s+(?:an?\s+)?[\w\s]{0,20}(?:problem|disease|infection|condition|disorder|cancer|issue|deficiency)|or\s+(?:something|somthing|sth)\s+(?:else|worse|serious)|what\s+(?:it\s+)?(?:is|could\s+be))|\b(?:cold\s+sores?|thyroid|diabet\w*|anemi\w*|nail\s+fungus|fungal\s+infection|staph|mrsa)\b[^.?!]{0,40}\?|\bwhat\s+(?:kind\s+of\s+|type\s+of\s+)?(?:skin\s+|scalp\s+|nail\s+)?(?:disease|condition|infection|illness|disorder)\b|\bwhat\s+(?:is|'?s)\s+(?:this|that|the)\s+(?:rash|lesion|lump|bump|growth|sore|spot|patch|cyst|boil)\b|\b(?:is|was)\s+(?:it|this|that|she|he|the\s+\w+)\b[^.?!]{0,50}\b(?:infected|contagious|cancer\w*|malignant|melanoma|eczema|psoriasis|ringworm|fung\w+\s+infection|alopecia|lupus|impetigo|allerg\w*|hormonal|dermatitis|rosacea|cellulitis|staph|mrsa|scabies|shingles|herpes|wart|tinea|folliculitis|serious|something\s+worse)\b|\b(?:it'?s|its|if\s+it'?s|it\s+is)\s+(?:an?\s+)?(?:melanoma|cancer\w*|skin\s+cancer|infected|contagious|eczema|psoriasis|ringworm|impetigo|lupus|scabies|mrsa|staph)\b|\b(?:eczema|psoriasis|melanoma|ringworm|impetigo|lupus|cradle\s+cap|cellulitis|scabies|shingles|herpes|tinea|rosacea|dermatitis)\s+or\s+|\bor\s+(?:something\s+worse|an?\s+(?:\w+\s+)?infection)\b|\b(?:is\s+(?:this|that|it)|could\s+(?:this|it|that|the\s+[\w\s]{1,30}?)\s+be|might\s+(?:this|it|that)\s+be)\s+(?:an?\s+)?(?:infection|infected|rash|disease|cancer\w*|melanoma|ringworm|eczema|psoriasis|impetigo|scabies|lupus|fung\w+|staph|mrsa|shingles|herpes|contagious|serious)\b`),
  },
  {
    id: 'legal', category: 'legal', route: 'human_qualified_professional',
    reason: 'immigration, employment and liability questions need a qualified human, not a mentor',
    test: (t) => /\bICE\b/.test(t) || LEGAL.test(t),
  },
  {
    id: 'harassment', category: 'harassment', route: 'human_title_ix',
    reason: 'harassment, threats or assault go to a trained human',
    re: /\b(harass\w*|threaten(?:ed|ing)?|assault(?:ed)?)\b/i,
  },
];

const hit = (t, text) => (t.test ? t.test(text) : t.re.test(text));

/**
 * Full classification: {id, category, route, reason, also[]} or null. `also`
 * lists every other trigger that fired so the eval can see overlaps.
 */
export function classifyEscalation(text) {
  const s = String(text ?? '');
  const fired = ESCALATION_TRIGGERS.filter((t) => hit(t, s));
  if (!fired.length) return null;
  const [top, ...rest] = fired;
  return { id: top.id, category: top.category, route: top.route, reason: top.reason,
           also: rest.map((t) => t.id) };
}

/** Back-compatible: the trigger id (a string) or null. */
export function detectEscalation(text) {
  return classifyEscalation(text)?.id ?? null;
}

/** The human-handoff line served on a crisis turn. Never a silent refusal. */
const HANDOFF_TO = {
  human_medical_referral: 'a medical professional through your instructor',
  human_instructor: 'your instructor',
  human_registrar: 'the registrar',
  human_qualified_professional: 'a qualified professional through your instructor',
  human_crisis: 'a person who can help right now',
};

export const CRISIS_HANDOFF =
  "I'm really glad you told me. I'm getting a person from the academy to you right now. " +
  'If you might act on this, call or text 988 (Suicide & Crisis Lifeline) or call 911 — you deserve support tonight.';

export const ESCALATION_CATEGORIES = Object.freeze(
  [...new Set(ESCALATION_TRIGGERS.map((t) => t.category))]);

/* -------------------------------------------------------------- mentor ----- */
/**
 * A mentor implementation supplies `respond(turn) -> {text, rung?, handoff?,
 * actions?}`. Everything else — redaction, scope enforcement, escalation,
 * rung clamping — happens here, identically for every mentor.
 */
export class Mentor {
  /**
   * @param {object} spec   {id, name, union, persona, scopes?}
   * @param {object} impl   {respond(turn, ctx)}
   */
  constructor(spec, impl) {
    this.spec = spec;
    this.impl = impl;
    this.scopes = spec.scopes ?? READ_SCOPES;
    this.version = spec.version ?? '0.1.0';
    this.telemetry = [];
  }

  read(surface, ctx) {
    if (!this.scopes.includes(surface)) throw new ScopeViolation(`read:${surface}`);
    return ctx[surface];
  }

  /**
   * One turn. Returns {text, rung, handoff, escalated, escalation, violations, redactions}.
   * `escalated` is the trigger id (or null); `escalation` carries {category, route, reason}.
   * A scope violation is CONTAINED, not thrown: the turn is refused, logged and
   * counted, because a mentor that tries something forbidden must be
   * measurable by the eval harness rather than crashing the hall.
   */
  async turn(input, ctx = {}) {
    const inRedact = redactPII(String(input));
    const escalation = classifyEscalation(inRedact.text);
    const escalated = escalation?.id ?? null;

    let raw;
    try {
      raw = await this.impl.respond({ text: inRedact.text, ...ctx }, ctx);
    } catch (err) {
      raw = { text: 'Let me get a human instructor for this one.', error: String(err) };
    }

    const violations = [];
    for (const a of raw?.actions ?? []) {
      if (FORBIDDEN_ACTIONS.includes(a)) violations.push(a);
    }

    // A mentor may never serve deeper help than the ladder allows here.
    //
    // The fallback is 0, not 5. It used to be 5, which meant that any caller
    // who forgot to stamp a ceiling got the FULL ladder including
    // co-completion — the sequencer stamped it only on verification picks, so
    // in practice every ordinary task ran unfaded (v2.7 defect 14). A missing
    // safeguard value must resolve to the most restrictive reading, never the
    // most permissive: an absent ceiling means nobody decided, and nobody
    // deciding is not permission.
    const ceiling = ctx.scaffold_ceiling ?? 0;
    const asked = ctx.requested_rung ?? 0;
    let rung = Math.max(0, Math.min(raw?.rung ?? 0, 5));
    const overHelped = rung > Math.max(asked, 0);
    rung = Math.min(rung, ceiling);

    const outRedact = redactPII(raw?.text ?? '');
    const record = {
      mentor: this.spec.id,
      version: this.version,
      rung,
      requested_rung: asked,
      over_helped: overHelped,
      handoff: raw?.handoff ?? null,
      escalated,
      escalation,
      violations,
      redactions: inRedact.redactions + outRedact.redactions,
      text: violations.length
        ? "That's not something I can do — I'll flag it for your instructor."
        : outRedact.text,
    };
    // An escalated turn is answered by the route, never by the mentor: the
    // model's own reply is not served (it is the thing we do not trust here).
    // A crisis gets the crisis handoff; every other category gets a handoff
    // naming who it is going to.
    if (escalated) {
      record.text = escalation?.category === 'crisis'
        ? CRISIS_HANDOFF
        : `This one needs a qualified person, not a training mentor. I'm passing it to ${HANDOFF_TO[escalation?.route] ?? 'your instructor'} now.`;
    }
    this.telemetry.push(record);
    return record;
  }
}
