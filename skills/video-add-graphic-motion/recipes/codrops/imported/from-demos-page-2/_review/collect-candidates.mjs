import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.join(outputDir, "CANDIDATES_RAW.json");
const pageCount = Number(process.argv[2] || 5);

function decodeHtml(value) {
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&#8217;|&rsquo;/g, "'")
    .replace(/&#038;/g, "&")
    .replace(/&quot;|&#8220;|&#8221;/g, '"')
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function absoluteUrl(href) {
  try {
    return new URL(href, "https://tympanus.net").href;
  } catch {
    return "";
  }
}

function parseArticle(article, pageUrl, pageNumber) {
  const titleMatch = article.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i);
  const anchors = [...article.matchAll(/<a\b[^>]*href=["']([^"']+)["']/gi)]
    .map((match) => absoluteUrl(match[1]))
    .filter(Boolean);
  const source = anchors.find((href) => /^https:\/\/github\.com\/codrops\//i.test(href)) || "";
  const articleUrl = anchors.find((href) => /tympanus\.net\/codrops\/20\d\d\//i.test(href)) || "";
  const rejectedPrefixes = [
    "https://tympanus.net/codrops/demos/",
    "https://tympanus.net/codrops/author/",
    "https://tympanus.net/codrops/licensing/",
    "https://github.com/codrops/",
  ];
  const demo = anchors.find((href) =>
    href !== articleUrl &&
    !rejectedPrefixes.some((prefix) => href.startsWith(prefix)) &&
    !href.includes("keycdn.com") &&
    !href.includes("readymag.com")
  ) || "";

  return {
    page: pageNumber,
    page_url: pageUrl,
    title: decodeHtml(titleMatch?.[1] || ""),
    demo_url: demo,
    article_url: articleUrl,
    source_url: source,
  };
}

const candidates = [];
for (let page = 1; page <= pageCount; page += 1) {
  const pageUrl = page === 1
    ? "https://tympanus.net/codrops/demos/"
    : `https://tympanus.net/codrops/demos/page/${page}/`;
  const response = await fetch(pageUrl);
  if (!response.ok) throw new Error(`${pageUrl}: HTTP ${response.status}`);
  const html = await response.text();
  const articles = [...html.matchAll(/<article\b[\s\S]*?<\/article>/gi)].map((match) => match[0]);
  const parsed = articles
    .map((article) => parseArticle(article, pageUrl, page))
    .filter((candidate) => candidate.title && candidate.demo_url && candidate.source_url);
  candidates.push(...parsed);
  console.log(`page ${page}: ${parsed.length} complete candidates`);
}

const unique = [...new Map(candidates.map((candidate) => [candidate.source_url.replace(/\/$/, ""), candidate])).values()];
await fs.writeFile(outputPath, `${JSON.stringify(unique, null, 2)}\n`, "utf8");
console.log(`wrote ${unique.length} unique candidates to ${outputPath}`);
