# GrowDaily Custom KJV Full Audit

## Result

**PASS**

## Files

- Original: `/home/liongateos/growdaily/assets/bible/en_kjv.json`
- Modified: `/home/liongateos/growdaily/assets/bible/kjv_modified.json`

## Structure Check

- PASS: Top-level JSON remains a 66-book list.
- PASS: Book abbreviations match.
- PASS: Chapter and verse counts match.

## Target Word Counts

| Word | Original | Modified |
|---|---:|---:|
| `Holy Ghost` | 90 | 0 |
| `Ghost` | 90 | 0 |
| `ghost` | 19 | 0 |
| `Adoption` | 0 | 0 |
| `adoption` | 5 | 0 |
| `scapegoat` | 4 | 0 |
| `Easter` | 1 | 0 |
| `Conversation` | 0 | 0 |
| `conversation` | 20 | 0 |

## Confirmed Replacement Word Counts

| Word | Original | Modified |
|---|---:|---:|
| `Holy Spirit` | 1 | 91 |
| `His Spirit` | 0 | 5 |
| `his spirit` | 17 | 24 |
| `her spirit` | 5 | 7 |
| `their spirit` | 2 | 3 |
| `my spirit` | 36 | 39 |
| `Sonship` | 0 | 0 |
| `sonship` | 0 | 5 |
| `Azazel` | 0 | 4 |
| `Passover` | 1 | 2 |
| `Conduct` | 0 | 0 |
| `conduct` | 3 | 23 |

## Remaining Target Hits

- PASS: No remaining target terms found anywhere in modified Bible JSON.

## Critical Verse Checks

- PASS: Luke 23:46 exact wording
- PASS: Acts 12:4 has Passover
- PASS: Leviticus 16 has no scapegoat

## Strong's / Bible Code Reference Scan

This does not modify app code. It lists places that must be checked before switching the app to `kjv_modified.json`.

- `logic/strongIndexLoader.js: file/path name contains strong`
- `logic/strongIndexLoader.js:1: import { isStrongsEnabled } from './strongFeatureFlag';`
- `logic/strongIndexLoader.js:5: * We intentionally do NOT require any Strong's index files yet.`
- `logic/strongIndexLoader.js:6: * This returns null unless Strong's is enabled AND an index exists.`
- `logic/strongIndexLoader.js:8: * Later (Phase 2+), we will add a real index file (assets/data/strong_index_en.json)`
- `logic/strongIndexLoader.js:13: export async function loadStrongsIndex() {`
- `logic/strongIndexLoader.js:14: if (!isStrongsEnabled()) return null;`
- `logic/strongIndexLoader.js:23: * Resolve a Strong's mapping for a verseKey + wordIndex.`
- `logic/strongIndexLoader.js:25: * - { strong: 'H7225', surface: 'beginning' } (example)`
- `logic/strongIndexLoader.js:28: export async function getStrongsMapping(verseKey, wordIndex) {`
- `logic/strongIndexLoader.js:29: const idx = await loadStrongsIndex();`
- `logic/strongIndexLoader.js:39: strong: found.strong ?? null,`
- `logic/strongWire.ts: file/path name contains strong`
- `logic/strongWire.ts:1: import { STRONGS_ENABLED } from "./strongFeatureFlag";`
- `logic/strongWire.ts:2: import { useStrongsLongPress } from "./useStrongsLongPress";`
- `logic/strongWire.ts:9: export function useStrongsIfEnabled() {`
- `logic/strongWire.ts:10: if (!STRONGS_ENABLED) {`
- `logic/strongWire.ts:15: const lp = useStrongsLongPress();`
- `logic/useStrongsLongPress.ts: file/path name contains strong`
- `logic/useStrongsLongPress.ts:2: import { STRONGS_ENABLED } from "./strongFeatureFlag";`
- `logic/useStrongsLongPress.ts:3: import { lookupStrongs, StrongsEntry } from "./strongIndex";`
- `logic/useStrongsLongPress.ts:5: export type UseStrongsLongPressResult = {`
- `logic/useStrongsLongPress.ts:7: entries: StrongsEntry[];`
- `logic/useStrongsLongPress.ts:13: export function useStrongsLongPress(): UseStrongsLongPressResult {`
- `logic/useStrongsLongPress.ts:15: const [entries, setEntries] = useState<StrongsEntry[]>([]);`
- `logic/useStrongsLongPress.ts:19: if (!STRONGS_ENABLED) return;`
- `logic/useStrongsLongPress.ts:20: const res = lookupStrongs(verseKey);`
- `logic/strongVerseKey.js: file/path name contains strong`
- `logic/strongVerseKey.js:7: * Builds canonical Strong's join key: Book:Chapter:Verse`
- `logic/strongFeatureFlag.js: file/path name contains strong`
- `logic/strongFeatureFlag.js:1: // logic/strongFeatureFlag.ts`
- `logic/strongFeatureFlag.js:4: // Enable Strong’s Concordance features globally.`
- `logic/strongFeatureFlag.js:6: // - Long-press Strong’s modal`
- `logic/strongFeatureFlag.js:7: // - Any Strong’s-dependent highlighting behavior`
- `logic/strongFeatureFlag.js:9: export const STRONGS_ENABLED = true;`
- `logic/strongWordTokenizer.js: file/path name contains strong`
- `logic/strongWordTokenizer.js:6: * - Provides wordIndex for Strong's mapping`
- `logic/BibleEngine.js:1: import kjv from "../assets/bible/en_kjv.json";`
- `logic/strongIndex.ts: file/path name contains strong`
- `logic/strongIndex.ts:1: // logic/strongIndex.ts`
- `logic/strongIndex.ts:2: // GrowDaily — Strong's Concordance live lookup`
- `logic/strongIndex.ts:5: //   assets/strong/strong_kjv.json       — verse/word → Strong's ID mapping`
- `logic/strongIndex.ts:6: //   assets/strong/strong_dict_hebrew.json — Hebrew dictionary (H####)`
- `logic/strongIndex.ts:7: //   assets/strong/strong_dict_greek.json  — Greek dictionary  (G####)`
- `logic/strongIndex.ts:9: // Called from BibleScreen: lookupStrongs("Genesis|1|1") → StrongsEntry[]`
- `logic/strongIndex.ts:11: import { STRONGS_ENABLED } from "./strongFeatureFlag";`
- `logic/strongIndex.ts:16: const strongKjv: { books: Record<string, Record<string, Record<string, Record<string, string>>>> } =`
- `logic/strongIndex.ts:17: require("../assets/strong/strong_kjv.json");`
- `logic/strongIndex.ts:21: require("../assets/strong/strong_dict_hebrew.json");`
- `logic/strongIndex.ts:25: require("../assets/strong/strong_dict_greek.json");`
- `logic/strongIndex.ts:29: export type StrongsEntry = {`
- `logic/strongIndex.ts:33: gloss:      string;   // core Strong's definition`
- `logic/strongIndex.ts:34: definition: string;   // KJV translation equivalents`
- `logic/strongIndex.ts:35: wordIndex:  number;   // source-order slot from strong_kjv.json`
- `logic/strongIndex.ts:36: occurrence: number;   // repeated occurrence count for the same Strong's ID`
- `logic/strongIndex.ts:39: export type LookupStrongsOptions = {`
- `logic/strongIndex.ts:43: type StrongsDictEntry = {`
- `logic/strongIndex.ts:55: return strongKjv?.books?.[book]?.[chapter]?.[verse] || null;`
- `logic/strongIndex.ts:58: function hydrateEntry(id: string, wordIndex: number, occurrence: number): StrongsEntry | null {`
- `logic/strongIndex.ts:60: const dict: Record<string, StrongsDictEntry> = id.startsWith("H") ? hebrewDict : greekDict;`
- `logic/strongIndex.ts:78: * Look up all Strong's entries for a verse.`
- `logic/strongIndex.ts:81: * @param options   Set dedupe=false to return every mapped Strong's slot in`
- `logic/strongIndex.ts:84: * @returns         One StrongsEntry per unique Strong's number in the verse by`
- `logic/strongIndex.ts:86: *                  Returns null if Strong's is disabled or the verse has no data.`
- `logic/strongIndex.ts:88: export function lookupStrongs(`
- `logic/strongIndex.ts:90: options: LookupStrongsOptions = {}`
- `logic/strongIndex.ts:91: ): StrongsEntry[] | null {`
- `logic/strongIndex.ts:92: if (!STRONGS_ENABLED) return null;`
- `logic/strongIndex.ts:106: const entries: StrongsEntry[] = [];`
- `logic/strongDictLoader.js: file/path name contains strong`
- `logic/strongDictLoader.js:1: import { isStrongsEnabled } from './strongFeatureFlag';`
- `logic/strongDictLoader.js:7: * - assets/data/strong_dict_hebrew.json`
- `logic/strongDictLoader.js:8: * - assets/data/strong_dict_greek.json`
- `logic/strongDictLoader.js:14: if (!isStrongsEnabled()) return null;`
- `logic/strongDictLoader.js:21: if (!isStrongsEnabled()) return null;`
- `logic/strongDictLoader.js:30: export async function getStrongsEntry(strongId) {`
- `logic/strongDictLoader.js:31: if (!isStrongsEnabled()) return null;`
- `logic/strongDictLoader.js:33: const id = (strongId ?? '').toString().trim();`
- `logic/bibleStore.js:5: const TRANSLATIONS = [`
- `logic/bibleStore.js:14: activeTranslation: "kjv_custom",`
- `logic/bibleStore.js:33: export function getAvailableTranslations() {`
- `logic/bibleStore.js:34: return TRANSLATIONS;`
- `logic/bibleStore.js:37: export async function getDownloadedTranslations() {`
- `logic/bibleStore.js:39: return TRANSLATIONS.filter((t) => data.downloaded.includes(t.id));`
- `logic/bibleStore.js:42: export async function downloadTranslation(id) {`
- `logic/bibleStore.js:44: if (!TRANSLATIONS.some((t) => t.id === id)) return false;`
- `logic/bibleStore.js:52: export async function setActiveTranslation(id) {`
- `logic/bibleStore.js:54: if (!TRANSLATIONS.some((t) => t.id === id)) return;`
- `logic/bibleStore.js:55: data.activeTranslation = id;`
- `logic/bibleStore.js:59: export async function getActiveTranslation() {`
- `logic/bibleStore.js:61: return data.activeTranslation || "kjv";`
- `logic/bibleStore.js:64: export async function isTranslationDownloaded(id) {`
- `logic/strongResolver.js: file/path name contains strong`
- `logic/strongResolver.js:2: // Strong's Resolver (read-only, safe)`
- `logic/strongResolver.js:6: import strongData from "../assets/strong/strong_kjv.json";`
- `logic/strongResolver.js:8: export function getStrongs(book, chapter, verse, wordIndex) {`
- `logic/strongResolver.js:11: const b = strongData.books?.[book];`
- `logic/strongVerseKey.ts: file/path name contains strong`
- `logic/strongFeatureFlag.ts: file/path name contains strong`
- `logic/strongFeatureFlag.ts:1: // logic/strongFeatureFlag.ts`
- `logic/strongFeatureFlag.ts:4: // Enable Strong’s Concordance features globally.`
- `logic/strongFeatureFlag.ts:6: // - Long-press Strong’s modal`
- `logic/strongFeatureFlag.ts:7: // - Any Strong’s-dependent highlighting behavior`
- `logic/strongFeatureFlag.ts:9: export const STRONGS_ENABLED = true;`
- `logic/strongsAlignmentLoader.js: file/path name contains strong`
- `logic/strongsAlignmentLoader.js:1: // logic/strongsAlignmentLoader.js`
- `logic/strongsAlignmentLoader.js:2: // GrowDaily — Phase 2 Strong's Alignment Runtime Loader`
- `logic/strongsAlignmentLoader.js:6: import { STRONGS_ENABLED } from "./strongFeatureFlag.js";`
- `logic/strongsAlignmentLoader.js:17: const ASSET_BASE_PATH = "/tmp/growdaily-strongs-alignment-assets";`
- `logic/strongsAlignmentLoader.js:24: if (!STRONGS_ENABLED) return null;`
- `logic/strongsAlignmentLoader.js:54: if (!STRONGS_ENABLED) return null;`
- `logic/strongsAlignmentLoader.js:84: // Validate translation ID`
- `logic/strongsAlignmentLoader.js:85: if (book.translationId !== "kjv_custom") {`
- `logic/strongsAlignmentLoader.js:86: console.warn("Unsupported translation ID for " + bookName + ": " + book.translationId);`
- `logic/strongsAlignmentLoader.js:101: * @param {string} translationId - Translation identifier (e.g., "kjv_custom")`
- `logic/strongsAlignmentLoader.js:107: export async function getVerseAlignment(translationId, book, chapter, verse) {`
- `logic/strongsAlignmentLoader.js:108: if (!STRONGS_ENABLED) return null;`
- `logic/strongsAlignmentLoader.js:110: // Validate translation ID`
- `logic/strongsAlignmentLoader.js:111: if (translationId !== "kjv_custom") {`
- `logic/strongsAlignmentLoader.js:112: console.warn("Unsupported translation ID: " + translationId);`
- `logic/strongsAlignmentLoader.js:134: * @param {string} translationId - Translation identifier`
- `logic/strongsAlignmentLoader.js:140: export async function getVerseAlignmentStatus(translationId, book, chapter, verse) {`
- `logic/strongsAlignmentLoader.js:141: const alignment = await getVerseAlignment(translationId, book, chapter, verse);`
- `screens/BibleScreen.js.before-phone-strongs-fix-20260607-215440: file/path name contains strong`
- `screens/BibleScreen.js.before-visible-strongs-modal-fix-20260607-215827: file/path name contains strong`
- `screens/JournalViewer.js:116: strong { font-weight: 700; }`
- `screens/BibleScreen.js:27: import bibleDataRaw from "../assets/bible/en_kjv.json";`
- `screens/BibleScreen.js:28: import bibleDataCustomRaw from "../assets/bible/kjv_modified.json";`
- `screens/BibleScreen.js:30: // Bible translations store`
- `screens/BibleScreen.js:32: getAvailableTranslations,`
- `screens/BibleScreen.js:33: getDownloadedTranslations,`
- `screens/BibleScreen.js:34: downloadTranslation as downloadBibleTranslation,`
- `screens/BibleScreen.js:35: setActiveTranslation,`
- `screens/BibleScreen.js:36: getActiveTranslation,`
- `screens/BibleScreen.js:37: isTranslationDownloaded,`
- `screens/BibleScreen.js:38: } from "../logic/bibleStore";`
- `screens/BibleScreen.js:41: import { isRedLetter } from "../logic/redLetters";`
- `screens/BibleScreen.js:57: // Strongs (verse-level lookup)`
- `screens/BibleScreen.js:58: import { lookupStrongs } from "../logic/strongIndex";`
- `screens/BibleScreen.js:59: import { STRONGS_ENABLED } from "../logic/strongFeatureFlag";`
- `screens/BibleScreen.js:64: // Translation data files (lazy require for non-KJV so bundler doesn't eagerly load them)`
- `screens/BibleScreen.js:254: // ── Translation state ──`
- `screens/BibleScreen.js:260: // Load saved translation preference on mount`
- `screens/BibleScreen.js:263: const id = await getActiveTranslation();`
- `screens/BibleScreen.js:264: const dl = await getDownloadedTranslations();`
- `screens/BibleScreen.js:287: const handleSelectTranslation = async (id) => {`
- `screens/BibleScreen.js:289: await setActiveTranslation(id);`
- `screens/BibleScreen.js:296: const ok = await downloadBibleTranslation(id);`
- `screens/BibleScreen.js:299: await setActiveTranslation(id);`
- `screens/BibleScreen.js:331: // Strongs modal (verse-level)`
- `screens/BibleScreen.js:332: const [strongsVisible, setStrongsVisible] = useState(false);`
- `screens/BibleScreen.js:333: const [strongsEntries, setStrongsEntries] = useState([]);`
- `screens/BibleScreen.js:334: const [strongsVerseRef, setStrongsVerseRef] = useState("");`
- `screens/BibleScreen.js:335: const [strongsMessage, setStrongsMessage] = useState("");`
- `screens/BibleScreen.js:337: const openStrongs = useCallback((verseKey, refLabel) => {`
- `screens/BibleScreen.js:339: if (!STRONGS_ENABLED) {`
- `screens/BibleScreen.js:340: setStrongsEntries([]);`
- `screens/BibleScreen.js:341: setStrongsVerseRef(`${refLabel} (Strongs disabled)`);`
- `screens/BibleScreen.js:342: setStrongsMessage("Strong’s Concordance is currently disabled.");`
- `screens/BibleScreen.js:343: setStrongsVisible(true);`
- `screens/BibleScreen.js:346: const res = lookupStrongs(verseKey, { dedupe: false });`
- `screens/BibleScreen.js:347: setStrongsEntries(Array.isArray(res) ? res : []);`
- `screens/BibleScreen.js:348: setStrongsVerseRef(refLabel);`
- `screens/BibleScreen.js:349: setStrongsMessage(`
- `screens/BibleScreen.js:352: : "No bundled Strong’s mappings were found for this verse."`
- `screens/BibleScreen.js:354: setStrongsVisible(true);`
- `screens/BibleScreen.js:357: const closeStrongs = useCallback(() => {`
- `screens/BibleScreen.js:358: setStrongsVisible(false);`
- `screens/BibleScreen.js:359: setStrongsEntries([]);`
- `screens/BibleScreen.js:360: setStrongsVerseRef("");`
- `screens/BibleScreen.js:361: setStrongsMessage("");`
- `screens/BibleScreen.js:383: const showRedLetters = activeTransId === "kjv" || activeTransId === "kjv_custom";`
- `screens/BibleScreen.js:470: const strongsUniqueCount = useMemo(() => {`
- `screens/BibleScreen.js:471: return new Set(strongsEntries.map((entry) => entry?.number).filter(Boolean)).size;`
- `screens/BibleScreen.js:472: }, [strongsEntries]);`
- `screens/BibleScreen.js:863: const isRed = showRedLetters && isRedLetter(v.book, v.chapter, v.verse);`
- `screens/BibleScreen.js:886: // Normal mode: tappable row, long-press for Strongs.`
- `screens/BibleScreen.js:893: onLongPress={() => openStrongs(v.verseKey, ref)}`
- `screens/BibleScreen.js:937: placeholder={`Search ${(BIBLE_DATA[activeTransId] ? (getAvailableTranslations().find(t => t.id === activeTransId)?.short || activeTransId) : 'KJV')} Bible…`}`
- `screens/BibleScreen.js:1131: showRedLetters &&`
- `screens/BibleScreen.js:1239: {/* Strongs Modal */}`
- `screens/BibleScreen.js:1241: visible={strongsVisible}`
- `screens/BibleScreen.js:1244: onRequestClose={closeStrongs}`
- `screens/BibleScreen.js:1246: <TouchableWithoutFeedback onPress={closeStrongs}>`
- `screens/BibleScreen.js:1250: <Text style={styles.modalTitle}>Strong's — {strongsVerseRef}</Text>`
- `screens/BibleScreen.js:1253: contentContainerStyle={[styles.strongsScrollContent, { paddingBottom: 20, paddingTop: 10 }]}`
- `screens/BibleScreen.js:1256: {(!strongsEntries || strongsEntries.length === 0) ? (`
- `screens/BibleScreen.js:1258: {strongsMessage || "No Strong's entries found for this verse."}`
- `screens/BibleScreen.js:1262: {strongsEntries.map((e, idx) => {`
- `screens/BibleScreen.js:1265: <View key={key} style={styles.strongsItem}>`
- `screens/BibleScreen.js:1266: <View style={styles.strongsItemHeader}>`
- `screens/BibleScreen.js:1267: <View style={styles.strongsNumberBadge}>`
- `screens/BibleScreen.js:1268: <Text style={styles.strongsId}>{e.number}</Text>`
- `screens/BibleScreen.js:1270: {!!e.lemma && <Text style={styles.strongsLemma}>{e.lemma}</Text>}`
- `screens/BibleScreen.js:1272: <View style={styles.strongsCountBadge}>`
- `screens/BibleScreen.js:1273: <Text style={styles.strongsCountBadgeText}>repeat {e.occurrence}</Text>`
- `screens/BibleScreen.js:1277: {!!e.translit && <Text style={styles.strongsTranslit}>({e.translit})</Text>}`
- `screens/BibleScreen.js:1278: {!!e.gloss && <Text style={styles.strongsGloss}>{e.gloss}</Text>}`
- `screens/BibleScreen.js:1279: {!!e.definition && <Text style={styles.strongsDef}>{e.definition}</Text>}`
- `screens/BibleScreen.js:1286: <Pressable style={styles.modalClose} onPress={closeStrongs}>`
- `screens/BibleScreen.js:1295: {/* Translations Modal */}`
- `screens/BibleScreen.js:1301: <Text style={styles.modalTitle}>Translations</Text>`
- `screens/BibleScreen.js:1302: {getAvailableTranslations().map((t) => {`
- `screens/BibleScreen.js:1317: <Pressable style={styles.transSelectBtn} onPress={() => handleSelectTranslation(t.id)}>`
- `screens/BibleScreen.js:1321: <Pressable style={styles.transDownloadBtn} onPress={() => handleSelectTranslation(t.id)}>`
- `screens/BibleScreen.js:1679: strongsMeta: {`
- `screens/BibleScreen.js:1684: strongsModalNote: {`
- `screens/BibleScreen.js:1690: strongsScrollContent: {`
- `screens/BibleScreen.js:1693: strongsListHeading: {`
- `screens/BibleScreen.js:1700: strongsItem: { marginBottom: 12 },`
- `screens/BibleScreen.js:1701: strongsItemHeader: {`
- `screens/BibleScreen.js:1707: strongsSlotBadge: {`
- `screens/BibleScreen.js:1717: strongsSlotBadgeText: {`
- `screens/BibleScreen.js:1722: strongsNumberBadge: {`
- `screens/BibleScreen.js:1730: strongsId: {`
- `screens/BibleScreen.js:1735: strongsLemma: {`
- `screens/BibleScreen.js:1741: strongsCountBadge: {`
- `screens/BibleScreen.js:1749: strongsCountBadgeText: {`
- `screens/BibleScreen.js:1754: strongsTranslit: { color: "#6f6aa8", fontSize: 12, fontStyle: "italic", marginTop: 1 },`
- `screens/BibleScreen.js:1755: strongsGloss: { color: "#fff", marginTop: 4, lineHeight: 19 },`
- `screens/BibleScreen.js:1756: strongsDef: { color: "#cfd3ff", marginTop: 4, lineHeight: 18 },`
- `screens/BibleScreen.js:1757: strongsLicenseNote: {`
- `screens/BibleScreen.js:2197: // Translations modal`
- `screens/CalendarScreen.js:366: // - Mr. Armstrong Death Anniversary (Jan 16, 1986)`
- `screens/CalendarScreen.js:376: { key: "hwa", title: "Mr. Armstrong Death Anniversary", month: 0, day: 16, startYear: 1986 },`
- `screens/JournalEditor.js:348: .ProseMirror strong { color: inherit; }`
- `screens/JournalEditor.js:491: `<p><strong>${verse.ref}</strong></p>` +`
- `screens/JournalEditor.js:496: `<p><strong>${verse.ref}</strong></p>` +`
- `screens/BibleScreen.js.before-fix-broken-strongs-text-20260607-222133: file/path name contains strong`
- `assets/strong/strong_dict_hebrew.json: file/path name contains strong`
- `assets/strong/strong_kjv.json: file/path name contains strong`
- `assets/strong/strong_dict_greek.json: file/path name contains strong`

## Strong's Safety Note

- The modified JSON preserves the same 66-book/chapter/verse structure.
- The app must not be switched to `kjv_modified.json` until Strong's lookup is confirmed to use stable references or a compatibility layer is added.
- If Strong's depends on exact visible KJV words, changed words such as `Satan`, `adoption`, `scapegoat`, `Easter`, `conversation`, and `ghost` need alias support.
