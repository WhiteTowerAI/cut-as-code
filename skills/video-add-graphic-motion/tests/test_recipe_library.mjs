import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  discoverRecipes,
  manifestList,
  materializeRecipe,
  searchRecipes,
  showRecipe,
} from "../scripts/recipe_library.mjs";

test("parses complete inline and block manifest lists", () => {
  assert.deepEqual(manifestList('tags: [one, "two, three"]\n', "tags"), ["one", "two, three"]);
  assert.deepEqual(
    manifestList("best_for:\n  - Short labels\n  - Technical terms\navoid_when: []\n", "best_for"),
    ["Short labels", "Technical terms"],
  );
});

async function addRecipe(root, surface, id, metadata) {
  const recipeDir = path.join(root, surface, id);
  await mkdir(path.join(recipeDir, "hyperframes", "source"), { recursive: true });
  const manifest = [
    `id: ${id}`,
    `name: ${metadata.name}`,
    `description: ${metadata.description}`,
    `category: ${metadata.category}`,
    `tags: [${metadata.tags.join(", ")}]`,
    `intent_keywords: [${metadata.intent_keywords.join(", ")}]`,
    `best_for: ["${metadata.best_for}"]`,
    `avoid_when: ["${metadata.avoid_when}"]`,
    "entry: preview.html",
    "runtime: [css, js]",
    "",
  ].join("\n");
  await writeFile(path.join(recipeDir, "recipe.motion.yaml"), manifest, "utf8");
  await writeFile(path.join(recipeDir, "hyperframes", "index.html"), `<div>${id}</div>`, "utf8");
  await writeFile(
    path.join(recipeDir, "hyperframes", "conversion.json"),
    JSON.stringify({ schema_version: 1, recipe_id: id }),
    "utf8",
  );
  await writeFile(
    path.join(recipeDir, "hyperframes", "source", "credit.js"),
    "/* Credit: Original Author */",
    "utf8",
  );
}

test("search returns a deterministic local shortlist with all seven selection fields", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "recipe-library-search-"));
  await addRecipe(root, "web", "signal-pulse", {
    name: "Signal Pulse",
    description: "A precise signal pulse resolves into ordered bars.",
    category: "data-visualization",
    tags: ["signal", "pulse", "bars"],
    intent_keywords: ["ordered signal", "data pulse"],
    best_for: "Explaining a noisy signal becoming ordered",
    avoid_when: "The frame already contains dense charts",
  });
  await addRecipe(root, "web", "calm-label", {
    name: "Calm Label",
    description: "A restrained text reveal.",
    category: "text-kinetic",
    tags: ["label", "calm"],
    intent_keywords: ["quiet title"],
    best_for: "Short editorial labels",
    avoid_when: "A signal pulse is required",
  });

  const first = await searchRecipes({ recipesRoot: root, query: "ordered signal pulse", limit: 8 });
  const second = await searchRecipes({ recipesRoot: root, query: "ordered signal pulse", limit: 8 });

  assert.deepEqual(first, second);
  assert.equal(first.length, 2);
  assert.equal(first[0].id, "signal-pulse");
  assert.deepEqual(Object.keys(first[0].metadata), [
    "name", "description", "category", "tags", "intent_keywords", "best_for", "avoid_when",
  ]);
  assert.ok(first[0].matched_fields.includes("name"));
  assert.ok(first[0].matched_fields.includes("intent_keywords"));
  assert.ok(first[1].avoid_when_matches.length > 0);
});

test("show resolves only manifest-backed recipes and exposes exact metadata", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "recipe-library-show-"));
  await addRecipe(root, "css", "wipe", {
    name: "Wipe",
    description: "A geometric wipe.",
    category: "transition",
    tags: ["wipe"],
    intent_keywords: ["scene transition"],
    best_for: "Section changes",
    avoid_when: "Continuous speech",
  });
  await mkdir(path.join(root, "imported", "fake"), { recursive: true });
  await writeFile(path.join(root, "imported", "fake", "recipe.motion.yaml"), "id: fake\n", "utf8");

  const recipes = await discoverRecipes(root);
  const recipe = await showRecipe({ recipesRoot: root, recipeId: "wipe" });

  assert.deepEqual(recipes.map((item) => item.id), ["wipe"]);
  assert.equal(recipe.metadata.best_for[0], "Section changes");
  await assert.rejects(
    showRecipe({ recipesRoot: root, recipeId: "fake" }),
    /unknown recipe id: fake/,
  );
});

test("materialize copies the preconverted recipe and returns project-relative hash bindings", async () => {
  const recipesRoot = await mkdtemp(path.join(os.tmpdir(), "recipe-library-materialize-"));
  const projectRoot = await mkdtemp(path.join(os.tmpdir(), "recipe-library-project-"));
  await addRecipe(recipesRoot, "web", "signal-pulse", {
    name: "Signal Pulse",
    description: "A signal pulse.",
    category: "data-visualization",
    tags: ["signal"],
    intent_keywords: ["signal pulse"],
    best_for: "Signal explanations",
    avoid_when: "Dense charts",
  });

  const result = await materializeRecipe({
    recipesRoot,
    recipeId: "signal-pulse",
    projectRoot,
    cueId: "gm-001",
  });

  assert.equal(result.id, "signal-pulse");
  assert.equal(result.composition_id, "signal-pulse");
  assert.ok(result.manifest.path.endsWith("/recipe.motion.yaml"));
  assert.ok(result.conversion_receipt.path.endsWith("/conversion.json"));
  assert.ok(result.files.some((item) => item.path.endsWith("/source/credit.js")));
  assert.ok(result.files.every((item) => !path.isAbsolute(item.path) && /^[0-9a-f]{64}$/.test(item.sha256)));
  const copiedCredit = path.join(
    projectRoot,
    "work", "cache", "graphic-motion", "hyperframes", "gm-001", "source", "credit.js",
  );
  assert.match(await readFile(copiedCredit, "utf8"), /Credit: Original Author/);
});
