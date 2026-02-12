import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function readIndexHtml(): string {
  return readFileSync(resolve(process.cwd(), "index.html"), "utf-8");
}

describe("frontend SEO metadata", () => {
  it("contains canonical and social metadata for the live site", () => {
    const html = readIndexHtml();

    expect(html).toContain("<title>Climate Index Console</title>");
    expect(html).toContain('name="description"');
    expect(html).toContain('rel="canonical" href="https://blizhan.github.io/climabc-index/"');
    expect(html).toContain('property="og:title"');
    expect(html).toContain('property="og:url" content="https://blizhan.github.io/climabc-index/"');
    expect(html).toContain('name="twitter:card"');
  });
});
