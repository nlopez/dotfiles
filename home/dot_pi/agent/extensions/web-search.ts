/**
 * Web Search Extension for pi
 *
 * Provides two tools:
 *   - web_search: Search the web using Kagi, Brave Search API, Serper.dev, or Google
 *   - fetch_url: Fetch and extract readable text from any URL
 *
 * Configuration (set one in your environment — checked in this order):
 *   KAGI_API_KEY              — https://kagi.com/settings?p=api       (paid, ~$0.025/search)
 *   BRAVE_API_KEY             — https://api.search.brave.com           (free tier: 2 000 queries/month)
 *   SERPER_API_KEY            — https://serper.dev                     (free tier: 2 500 queries)
 *   GOOGLE_API_KEY +          — https://developers.google.com/custom-search/v1/introduction
 *   GOOGLE_CSE_ID               (free tier: 100 queries/day)
 *
 * Placement: ~/.pi/agent/extensions/web-search.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

// ---------------------------------------------------------------------------
// HTML → plain-text helper
// ---------------------------------------------------------------------------

function stripHtml(html: string): string {
	return html
		.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
		.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, "")
		.replace(/<\/?(p|div|br|li|tr|h[1-6])\b[^>]*>/gi, "\n")
		.replace(/<[^>]+>/g, "")
		.replace(/&amp;/g, "&")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.replace(/&nbsp;/g, " ")
		.replace(/[ \t]+/g, " ")
		.replace(/\n{3,}/g, "\n\n")
		.trim();
}

// ---------------------------------------------------------------------------
// Search providers
// ---------------------------------------------------------------------------

interface SearchResult {
	content: { type: "text"; text: string }[];
	details: Record<string, unknown>;
}

async function searchKagi(
	query: string,
	count: number,
	signal: AbortSignal | undefined,
): Promise<SearchResult> {
	const url = new URL("https://kagi.com/api/v0/search");
	url.searchParams.set("q", query);
	url.searchParams.set("limit", String(count));

	const response = await fetch(url.toString(), {
		signal,
		headers: {
			Authorization: `Bot ${process.env.KAGI_API_KEY}`,
		},
	});

	if (!response.ok) {
		throw new Error(`Kagi Search API error: ${response.status} ${response.statusText}`);
	}

	const data = (await response.json()) as {
		data?: {
			t: number; // 0 = web result, 1 = related searches
			rank?: number;
			url?: string;
			title?: string;
			snippet?: string;
			published?: string;
		}[];
	};

	const results = (data.data ?? [])
		.filter((r) => r.t === 0 && r.url) // web results only
		.slice(0, count);

	const text =
		results
			.map((r, i) => {
				const published = r.published
					? ` (${new Date(r.published).toISOString().slice(0, 10)})`
					: "";
				return `${i + 1}. **${r.title ?? ""}**${published}\n   ${r.url}\n   ${r.snippet ?? ""}`;
			})
			.join("\n\n") || "No results found.";

	return {
		content: [{ type: "text", text }],
		details: { query, count: results.length, provider: "Kagi" },
	};
}

async function searchGoogle(
	query: string,
	count: number,
	signal: AbortSignal | undefined,
): Promise<SearchResult> {
	const url = new URL("https://www.googleapis.com/customsearch/v1");
	url.searchParams.set("key", process.env.GOOGLE_API_KEY!);
	url.searchParams.set("cx", process.env.GOOGLE_CSE_ID!);
	url.searchParams.set("q", query);
	url.searchParams.set("num", String(Math.min(count, 10)));

	const response = await fetch(url.toString(), { signal });

	if (!response.ok) {
		throw new Error(`Google Custom Search API error: ${response.status} ${response.statusText}`);
	}

	const data = (await response.json()) as {
		items?: { title: string; link: string; snippet?: string }[];
	};
	const results = (data.items ?? []).slice(0, count);

	const text =
		results
			.map((r, i) => `${i + 1}. **${r.title}**\n   ${r.link}\n   ${r.snippet ?? ""}`)
			.join("\n\n") || "No results found.";

	return {
		content: [{ type: "text", text }],
		details: { query, count: results.length, provider: "Google" },
	};
}

async function searchBrave(
	query: string,
	count: number,
	signal: AbortSignal | undefined,
): Promise<SearchResult> {
	const url = new URL("https://api.search.brave.com/res/v1/web/search");
	url.searchParams.set("q", query);
	url.searchParams.set("count", String(count));

	const response = await fetch(url.toString(), {
		signal,
		headers: {
			Accept: "application/json",
			"Accept-Encoding": "gzip",
			"X-Subscription-Token": process.env.BRAVE_API_KEY!,
		},
	});

	if (!response.ok) {
		throw new Error(`Brave Search API error: ${response.status} ${response.statusText}`);
	}

	const data = (await response.json()) as {
		web?: { results?: { title: string; url: string; description?: string }[] };
	};
	const results = (data.web?.results ?? []).slice(0, count);

	const text =
		results
			.map((r, i) => `${i + 1}. **${r.title}**\n   ${r.url}\n   ${r.description ?? ""}`)
			.join("\n\n") || "No results found.";

	return {
		content: [{ type: "text", text }],
		details: { query, count: results.length, provider: "Brave" },
	};
}

async function searchSerper(
	query: string,
	count: number,
	signal: AbortSignal | undefined,
): Promise<SearchResult> {
	const response = await fetch("https://google.serper.dev/search", {
		method: "POST",
		signal,
		headers: {
			"Content-Type": "application/json",
			"X-API-KEY": process.env.SERPER_API_KEY!,
		},
		body: JSON.stringify({ q: query, num: count }),
	});

	if (!response.ok) {
		throw new Error(`Serper API error: ${response.status} ${response.statusText}`);
	}

	const data = (await response.json()) as {
		answerBox?: { answer?: string; snippet?: string };
		organic?: { title: string; link: string; snippet?: string }[];
	};

	let text = "";

	if (data.answerBox) {
		const ab = data.answerBox;
		const answer = ab.answer ?? ab.snippet ?? "";
		if (answer) text += `**Answer:** ${answer}\n\n`;
	}

	const results = (data.organic ?? []).slice(0, count);
	text +=
		results
			.map((r, i) => `${i + 1}. **${r.title}**\n   ${r.link}\n   ${r.snippet ?? ""}`)
			.join("\n\n") || "No results found.";

	return {
		content: [{ type: "text", text: text.trim() }],
		details: { query, count: results.length, provider: "Serper" },
	};
}

// ---------------------------------------------------------------------------
// Extension entry point
// ---------------------------------------------------------------------------

export default function (pi: ExtensionAPI) {
	// ── web_search ────────────────────────────────────────────────────────────
	pi.registerTool({
		name: "web_search",
		label: "Web Search",
		description:
			"Search the web for up-to-date information. " +
			"Requires KAGI_API_KEY, BRAVE_API_KEY, SERPER_API_KEY, or " +
			"GOOGLE_API_KEY + GOOGLE_CSE_ID in the environment.",
		promptSnippet: "Search the web for current information",
		promptGuidelines: [
			"Use web_search when the user asks about recent events, live data, or anything that may have changed after the model's training cutoff.",
			"After web_search, use fetch_url to retrieve the full content of a promising result page.",
		],
		parameters: Type.Object({
			query: Type.String({ description: "Search query" }),
			count: Type.Optional(
				Type.Number({ description: "Number of results to return (default: 5, max: 10)" }),
			),
		}),
		async execute(_toolCallId, params, signal) {
			const count = Math.min(params.count ?? 5, 10);

			if (process.env.KAGI_API_KEY) {
				return searchKagi(params.query, count, signal);
			}
			if (process.env.BRAVE_API_KEY) {
				return searchBrave(params.query, count, signal);
			}
			if (process.env.SERPER_API_KEY) {
				return searchSerper(params.query, count, signal);
			}
			if (process.env.GOOGLE_API_KEY && process.env.GOOGLE_CSE_ID) {
				return searchGoogle(params.query, count, signal);
			}

			throw new Error(
				"No search API key found.\n" +
					"Set KAGI_API_KEY (https://kagi.com/settings?p=api)\n" +
					"or BRAVE_API_KEY (https://api.search.brave.com, free tier: 2 000 queries/month)\n" +
					"or SERPER_API_KEY (https://serper.dev, free tier: 2 500 queries)\n" +
					"or GOOGLE_API_KEY + GOOGLE_CSE_ID (https://developers.google.com/custom-search/v1/introduction, free tier: 100 queries/day).",
			);
		},
	});

	// ── fetch_url ─────────────────────────────────────────────────────────────
	pi.registerTool({
		name: "fetch_url",
		label: "Fetch URL",
		description:
			"Fetch the contents of a URL and return readable text. " +
			"HTML is stripped to plain text. Useful for reading search results.",
		promptSnippet: "Fetch and read the text content of a web page",
		parameters: Type.Object({
			url: Type.String({ description: "URL to fetch" }),
			max_chars: Type.Optional(
				Type.Number({
					description: "Maximum characters to return (default: 8000)",
				}),
			),
		}),
		async execute(_toolCallId, params, signal) {
			const maxChars = params.max_chars ?? 8000;

			const response = await fetch(params.url, {
				signal,
				headers: {
					"User-Agent":
						"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
						"(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
					Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
				},
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status} ${response.statusText} — ${params.url}`);
			}

			const contentType = response.headers.get("content-type") ?? "";
			const raw = await response.text();

			let content = contentType.includes("html") ? stripHtml(raw) : raw;

			const truncated = content.length > maxChars;
			if (truncated) {
				content =
					content.slice(0, maxChars) +
					`\n\n[… truncated — ${content.length - maxChars} more characters not shown]`;
			}

			return {
				content: [{ type: "text", text: content }],
				details: { url: params.url, contentType, truncated },
			};
		},
	});

	// Notify on startup if no API key is configured
	pi.on("session_start", async (_event, ctx) => {
		const hasGoogle = !!(process.env.GOOGLE_API_KEY && process.env.GOOGLE_CSE_ID);
		if (!process.env.KAGI_API_KEY && !process.env.BRAVE_API_KEY && !process.env.SERPER_API_KEY && !hasGoogle) {
			ctx.ui.notify(
				"web-search: no API key found — set KAGI_API_KEY, BRAVE_API_KEY, SERPER_API_KEY, or GOOGLE_API_KEY+GOOGLE_CSE_ID to enable web_search",
				"warn",
			);
		}
	});
}
