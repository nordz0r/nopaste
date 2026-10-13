// Exposes window.NopastePrLens.render(jsonText, lens, theme) -> { lens, lenses, svg }.
// The SVG string must only ever be displayed through <img src="blob:..."> (see prlens-view.js).
import { render } from "@coldtea/pr-lens-renderer";
import { GraphDoc } from "@coldtea/pr-lens-schema";

window.NopastePrLens = {
  render(jsonText, lens, theme) {
    let raw;
    try {
      raw = JSON.parse(jsonText);
    } catch (err) {
      throw new Error(`graph.json is not valid JSON (${err.message})`);
    }
    const parsed = GraphDoc.safeParse(raw);
    if (!parsed.success) {
      const issues = parsed.error.issues.slice(0, 3).map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`);
      throw new Error(`graph.json does not match PR Lens schema: ${issues.join("; ")}`);
    }
    const doc = parsed.data;
    const lenses = Array.isArray(doc.lenses) ? doc.lenses : [];
    const selected = lens && lenses.includes(lens) ? lens : lenses[0] || "architecture";
    const out = render(doc, { lens: selected, theme: theme === "light" ? "light" : "dark" });
    return { lens: selected, lenses, svg: out.svg };
  },
};
