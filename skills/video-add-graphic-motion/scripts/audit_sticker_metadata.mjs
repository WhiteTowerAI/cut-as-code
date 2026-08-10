#!/usr/bin/env node

import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditConvertedRecipes } from "./convert_motion_anything_recipes.mjs";
import { discoverRecipes, rankRecipes } from "./recipe_library.mjs";
import {
  STICKER_CATEGORIES,
  buildStickerProfiles,
  semanticBaseForLineMd,
  validateStickerProfiles,
} from "./sticker_semantics.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(skillRoot, "..", "..");
const recipesRoot = path.join(skillRoot, "recipes");
const benchmarkPath = path.join(skillRoot, "reference", "sticker-selection-benchmark.json");
const cacheRoot = path.join(repoRoot, "work", "cache", "sticker-metadata");
const outputPath = path.resolve(process.argv[2] || path.join(cacheRoot, "acceptance-report.json"));
const beforeHashPath = path.join(cacheRoot, "before-render-hashes.json");
const afterHashPath = path.join(cacheRoot, "after-render-hashes.json");

const STICKER_COUNTS = Object.freeze({
  "canvas-confetti": 10,
  mojs: 10,
  "line-md": 1222,
  meteocons: 12,
  tsparticles: 4,
});
const STICKER_SURFACES = new Set(Object.keys(STICKER_COUNTS));
const FORBIDDEN_ROUTING_TERMS = new Set([
  "sticker", "line-md", "meteocons", "mojs", "tsparticles", "svg", "svg-smil", "javascript", "js",
]);
const MOJIBAKE = /\ufffd|(?:閻|鐟|缁|閸|閿)/u;

async function walk(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(target));
    else files.push(target);
  }
  return files;
}

function listErrors(recipe) {
  const errors = [];
  const { metadata } = recipe;
  const words = metadata.name.trim().split(/\s+/u).filter(Boolean).length;
  if (words < 2 || words > 8) errors.push("name must contain 2-8 words");
  if (metadata.description.length < 40 || !metadata.description.endsWith(".")) errors.push("invalid description");
  if (!STICKER_CATEGORIES.includes(metadata.category)) errors.push(`invalid category ${metadata.category}`);
  for (const [field, min, max] of [
    ["tags", 6, 10], ["intent_keywords", 8, 16], ["best_for", 2, 4], ["avoid_when", 2, 4],
  ]) {
    const values = metadata[field];
    if (values.length < min || values.length > max) errors.push(`${field} must contain ${min}-${max} items`);
    if (new Set(values).size !== values.length) errors.push(`${field} contains duplicates`);
  }
  if (metadata.intent_keywords.filter((item) => /^[\x00-\x7f]+$/u.test(item)).length < 5) {
    errors.push("intent_keywords needs at least five English entries");
  }
  if (metadata.intent_keywords.filter((item) => /\p{Script=Han}/u.test(item)).length < 3) {
    errors.push("intent_keywords needs at least three Chinese entries");
  }
  if (metadata.tags.some((item) => FORBIDDEN_ROUTING_TERMS.has(item))) errors.push("tags contain generic routing terms");
  if (metadata.intent_keywords.some((item) => FORBIDDEN_ROUTING_TERMS.has(item))) errors.push("intent_keywords contain generic routing terms");
  if (JSON.stringify(metadata.tags) === JSON.stringify(metadata.intent_keywords)) errors.push("tags copied to intent_keywords");
  if (MOJIBAKE.test(JSON.stringify(metadata))) errors.push("metadata contains mojibake");
  return errors.map((error) => `${recipe.id}: ${error}`);
}

function compareHashes(before, after) {
  const paths = new Set([...Object.keys(before.hashes), ...Object.keys(after.hashes)]);
  const differences = [];
  for (const file of [...paths].sort()) {
    if (before.hashes[file] !== after.hashes[file]) {
      differences.push({ path: file, before: before.hashes[file] || null, after: after.hashes[file] || null });
    }
  }
  return { before_count: before.file_count, after_count: after.file_count, differences };
}

function evaluateBenchmark(recipes, benchmark) {
  const cases = [];
  let top5Hits = 0;
  let categoryTop1Hits = 0;
  let reciprocalRankTotal = 0;
  let hardConflicts = 0;
  let avoidOnlyResults = 0;
  for (const group of benchmark.groups) {
    for (const query of group.queries) {
      const results = rankRecipes(recipes, { query: query.query, limit: 50 });
      const expectedIndex = results.findIndex((result) => (
        group.expected_id_prefixes.some((prefix) => result.id.startsWith(prefix))
      ));
      const expectedRank = expectedIndex + 1;
      const top5 = expectedRank > 0 && expectedRank <= 5;
      const categoryTop1 = results[0]?.metadata.category === group.category;
      const hardConflict = Boolean(results[0] && group.forbidden_categories.includes(results[0].metadata.category));
      const avoidOnly = results.filter((result) => result.score <= 0).map((result) => result.id);
      if (top5) top5Hits += 1;
      if (categoryTop1) categoryTop1Hits += 1;
      if (expectedRank) reciprocalRankTotal += 1 / expectedRank;
      if (hardConflict) hardConflicts += 1;
      avoidOnlyResults += avoidOnly.length;
      if (!top5 || !categoryTop1 || hardConflict || avoidOnly.length) {
        cases.push({
          language: query.language,
          query: query.query,
          expected_category: group.category,
          expected_rank: expectedRank || null,
          top_result: results[0] ? { id: results[0].id, category: results[0].metadata.category, score: results[0].score } : null,
          hard_conflict: hardConflict,
          avoid_only_results: avoidOnly,
        });
      }
    }
  }
  const total = benchmark.groups.reduce((count, group) => count + group.queries.length, 0);
  return {
    query_count: total,
    top5_rate: top5Hits / total,
    category_top1_rate: categoryTop1Hits / total,
    mrr: reciprocalRankTotal / total,
    hard_conflicts: hardConflicts,
    avoid_only_results: avoidOnlyResults,
    failing_cases: cases,
  };
}

const recipes = await discoverRecipes(recipesRoot);
const stickerRecipes = recipes.filter((recipe) => STICKER_SURFACES.has(recipe.surface));
const lineMdRecipes = stickerRecipes.filter((recipe) => recipe.surface === "line-md");
const lineMdBaseCount = new Set(lineMdRecipes.map((recipe) => (
  semanticBaseForLineMd(recipe.id.slice("line-md-".length)).base
))).size;
const lineMdVariantCount = lineMdRecipes.length - lineMdBaseCount;
const lineMdData = JSON.parse(await readFile(
  path.join(repoRoot, "work", "cache", "sticker-sources", "line-md", "line-md.json"),
  "utf8",
));
const profiles = buildStickerProfiles(lineMdData);
const profileErrors = validateStickerProfiles(profiles);
const counts = Object.fromEntries(Object.keys(STICKER_COUNTS).map((surface) => [
  surface,
  stickerRecipes.filter((recipe) => recipe.surface === surface).length,
]));
const fieldErrors = stickerRecipes.flatMap(listErrors);
const benchmark = JSON.parse(await readFile(benchmarkPath, "utf8"));
const benchmarkResult = evaluateBenchmark(recipes, benchmark);
const renderHashes = compareHashes(
  JSON.parse(await readFile(beforeHashPath, "utf8")),
  JSON.parse(await readFile(afterHashPath, "utf8")),
);
const notoHits = stickerRecipes.flatMap((recipe) => {
  const identity = `${recipe.id}\n${recipe.recipeDir}\n${JSON.stringify(recipe.metadata)}`.toLocaleLowerCase();
  return identity.includes("noto") ? [recipe.id] : [];
});
const staticAudit = await auditConvertedRecipes(recipesRoot);
const countsOk = stickerRecipes.length === 1258
  && recipes.length === 1477
  && Object.entries(STICKER_COUNTS).every(([surface, count]) => counts[surface] === count);
const ok = countsOk
  && profiles.size === 568
  && lineMdBaseCount === 532
  && lineMdVariantCount === 690
  && profileErrors.length === 0
  && fieldErrors.length === 0
  && benchmarkResult.top5_rate >= 0.95
  && benchmarkResult.category_top1_rate >= 0.90
  && benchmarkResult.mrr >= 0.75
  && benchmarkResult.hard_conflicts === 0
  && benchmarkResult.avoid_only_results === 0
  && notoHits.length === 0
  && renderHashes.before_count === 11298
  && renderHashes.after_count === 11298
  && renderHashes.differences.length === 0
  && staticAudit.recipe_count === 1477
  && staticAudit.converted_count === 1477
  && staticAudit.errors.length === 0;

const report = {
  schema_version: 1,
  ok,
  thresholds: { top5_rate: 0.95, category_top1_rate: 0.90, mrr: 0.75 },
  counts: {
    total_recipes: recipes.length,
    sticker_recipes: stickerRecipes.length,
    semantic_profiles: profiles.size,
    line_md_bases: lineMdBaseCount,
    line_md_variants: lineMdVariantCount,
    by_surface: counts,
  },
  profile_quality: { error_count: profileErrors.length, errors: profileErrors },
  field_quality: { error_count: fieldErrors.length, errors: fieldErrors },
  benchmark: benchmarkResult,
  noto: { hit_count: notoHits.length, hits: notoHits },
  render_hashes: renderHashes,
  static_audit: staticAudit,
};

await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ output: outputPath, ok, benchmark: benchmarkResult, field_errors: fieldErrors.length, noto_hits: notoHits.length, render_hash_differences: renderHashes.differences.length, static_errors: staticAudit.errors.length })}\n`);
if (!ok) process.exitCode = 1;
