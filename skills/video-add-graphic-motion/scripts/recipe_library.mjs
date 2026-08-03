#!/usr/bin/env node

import crypto from "node:crypto";
import { cp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const SELECTION_FIELDS = [
  "name",
  "description",
  "category",
  "tags",
  "intent_keywords",
  "best_for",
  "avoid_when",
];

const POSITIVE_WEIGHTS = {
  name: 8,
  description: 4,
  category: 3,
  tags: 6,
  intent_keywords: 7,
  best_for: 5,
};

function unquote(value) {
  const text = String(value).trim();
  if (
    text.length >= 2
    && ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'")))
  ) {
    return text.slice(1, -1);
  }
  return text;
}

export function manifestScalar(manifest, key) {
  const match = manifest.match(new RegExp(`^${key}:[ \\t]*([^#\\r\\n]*)`, "m"));
  return match && match[1].trim() ? unquote(match[1]) : null;
}

export function manifestList(manifest, key) {
  const value = manifestScalar(manifest, key);
  if (value) {
    const bracketed = value.match(/^\[(.*)\]$/);
    if (!bracketed) return [value];
    return [...bracketed[1].matchAll(/\s*(?:"(?:\\.|[^"])*"|'(?:\\.|[^'])*'|[^,]+)/g)]
      .map((match) => unquote(match[0]))
      .filter(Boolean);
  }
  const lines = manifest.split(/\r?\n/);
  const start = lines.findIndex((line) => new RegExp(`^${key}:[ \\t]*$`).test(line));
  if (start < 0) return [];
  const items = [];
  for (const line of lines.slice(start + 1)) {
    if (/^[A-Za-z_][A-Za-z0-9_-]*:/.test(line)) break;
    const match = line.match(/^\s+-\s+(.+)$/);
    if (match) items.push(unquote(match[1]));
  }
  return items;
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

async function walk(directory, skipDirectories = new Set()) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory() && !skipDirectories.has(entry.name)) {
      files.push(...(await walk(target, skipDirectories)));
    } else if (entry.isFile()) {
      files.push(target);
    }
  }
  return files;
}

function metadataFromManifest(manifest) {
  return {
    name: manifestScalar(manifest, "name") || "",
    description: manifestScalar(manifest, "description") || "",
    category: manifestScalar(manifest, "category") || "",
    tags: manifestList(manifest, "tags"),
    intent_keywords: manifestList(manifest, "intent_keywords"),
    best_for: manifestList(manifest, "best_for"),
    avoid_when: manifestList(manifest, "avoid_when"),
  };
}

export async function discoverRecipes(recipesRoot) {
  const root = path.resolve(recipesRoot);
  const manifests = (await walk(root, new Set(["imported", "hyperframes"])))
    .filter((file) => path.basename(file) === "recipe.motion.yaml")
    .sort((left, right) => left.localeCompare(right));
  const recipes = await Promise.all(manifests.map(async (manifestPath) => {
    const manifest = await readFile(manifestPath, "utf8");
    const recipeDir = path.dirname(manifestPath);
    return {
      id: manifestScalar(manifest, "id") || path.basename(recipeDir),
      surface: path.basename(path.dirname(recipeDir)),
      recipeDir,
      manifestPath,
      manifest,
      metadata: metadataFromManifest(manifest),
      runtime: manifestList(manifest, "runtime"),
      entry: manifestScalar(manifest, "entry") || "preview.html",
    };
  }));
  const ids = new Set();
  for (const recipe of recipes) {
    if (ids.has(recipe.id)) throw new Error(`duplicate recipe id: ${recipe.id}`);
    ids.add(recipe.id);
  }
  return recipes;
}

function words(value) {
  return [...String(value).toLocaleLowerCase().matchAll(/[\p{L}\p{N}]+/gu)].map((match) => match[0]);
}

function fieldText(value) {
  return Array.isArray(value) ? value.join(" ") : String(value || "");
}

export async function searchRecipes({ recipesRoot, query = "", category = null, limit = 8 }) {
  const queryWords = [...new Set(words(query))];
  const normalizedCategory = category ? String(category).toLocaleLowerCase() : null;
  const recipes = await discoverRecipes(recipesRoot);
  const results = [];
  for (const recipe of recipes) {
    if (normalizedCategory && recipe.metadata.category.toLocaleLowerCase() !== normalizedCategory) continue;
    const matchedFields = [];
    let score = 0;
    for (const [field, weight] of Object.entries(POSITIVE_WEIGHTS)) {
      const tokens = new Set(words(fieldText(recipe.metadata[field])));
      const matches = queryWords.filter((token) => tokens.has(token));
      if (matches.length) matchedFields.push(field);
      score += matches.length * weight;
    }
    const avoidTokens = new Set(words(fieldText(recipe.metadata.avoid_when)));
    const avoidWhenMatches = queryWords.filter((token) => avoidTokens.has(token));
    if (queryWords.length && score === 0 && avoidWhenMatches.length === 0) continue;
    results.push({
      id: recipe.id,
      surface: recipe.surface,
      score,
      matched_fields: matchedFields,
      avoid_when_matches: avoidWhenMatches,
      metadata: recipe.metadata,
    });
  }
  results.sort((left, right) => right.score - left.score || left.id.localeCompare(right.id));
  const parsedLimit = Number(limit);
  if (!Number.isInteger(parsedLimit) || parsedLimit < 1 || parsedLimit > 50) {
    throw new Error("limit must be an integer from 1 to 50");
  }
  return results.slice(0, parsedLimit);
}

export async function showRecipe({ recipesRoot, recipeId }) {
  const recipe = (await discoverRecipes(recipesRoot)).find((item) => item.id === recipeId);
  if (!recipe) throw new Error(`unknown recipe id: ${recipeId}`);
  const conversionPath = path.join(recipe.recipeDir, "hyperframes", "conversion.json");
  const conversion = await readFile(conversionPath);
  return {
    id: recipe.id,
    surface: recipe.surface,
    runtime: recipe.runtime,
    entry: recipe.entry,
    metadata: recipe.metadata,
    manifest_sha256: sha256(Buffer.from(recipe.manifest)),
    conversion_receipt_sha256: sha256(conversion),
  };
}

function projectBinding(projectRoot, file, bytes) {
  return {
    path: path.relative(projectRoot, file).split(path.sep).join("/"),
    sha256: sha256(bytes),
  };
}

export async function materializeRecipe({ recipesRoot, recipeId, projectRoot, cueId }) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(String(cueId || ""))) {
    throw new Error("cue id must contain only letters, numbers, dot, underscore, or hyphen");
  }
  const recipe = (await discoverRecipes(recipesRoot)).find((item) => item.id === recipeId);
  if (!recipe) throw new Error(`unknown recipe id: ${recipeId}`);
  const source = path.join(recipe.recipeDir, "hyperframes");
  const root = path.resolve(projectRoot);
  const target = path.join(root, "work", "cache", "graphic-motion", "hyperframes", cueId);
  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });
  await cp(source, target, { recursive: true, force: true });
  await writeFile(path.join(target, "recipe.motion.yaml"), recipe.manifest, "utf8");
  const copiedFiles = (await walk(target)).sort((left, right) => left.localeCompare(right));
  const files = await Promise.all(copiedFiles.map(async (file) => {
    const bytes = await readFile(file);
    return projectBinding(root, file, bytes);
  }));
  const byName = (name) => files.find((binding) => binding.path.endsWith(`/${name}`));
  return {
    id: recipe.id,
    composition_id: recipe.id,
    manifest: byName("recipe.motion.yaml"),
    conversion_receipt: byName("conversion.json"),
    files,
  };
}

function option(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

async function main(args) {
  const command = args[0];
  const recipesRoot = path.resolve(fileURLToPath(new URL("../recipes", import.meta.url)));
  let result;
  if (command === "search") {
    result = await searchRecipes({
      recipesRoot,
      query: option(args, "--query", ""),
      category: option(args, "--category"),
      limit: Number(option(args, "--limit", "8")),
    });
  } else if (command === "show") {
    result = await showRecipe({ recipesRoot, recipeId: args[1] });
  } else if (command === "materialize") {
    result = await materializeRecipe({
      recipesRoot,
      recipeId: args[1],
      projectRoot: option(args, "--project"),
      cueId: option(args, "--cue"),
    });
  } else {
    throw new Error(
      "usage: recipe_library.mjs search --query <text> [--category <id>] [--limit 8] --json\n"
      + "       recipe_library.mjs show <recipe-id> --json\n"
      + "       recipe_library.mjs materialize <recipe-id> --project <root> --cue <cue-id> --json",
    );
  }
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
