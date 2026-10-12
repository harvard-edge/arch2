```{=html}
<div class="tool-listing list">
<%
const pandocSafe = (value) => String(value ?? "")
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");
const pandocHttpUrl = (value) => {
  try {
    const url = new URL(String(value ?? ""));
    return ["http:", "https:"].includes(url.protocol) ? pandocSafe(url.href) : "#";
  } catch {
    return "#";
  }
};
const classToken = (value) => String(value ?? "")
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-|-$/g, "");
const availabilityLabels = {
  runnable: "Runnable",
  source_available: "Source available",
  benchmark_available: "Benchmark available",
  dataset_available: "Dataset available",
  paper_only: "Paper only",
  unverified: "Unverified",
};
%>
<% for (const item of items) { %>
  <% const primaryUrl = pandocHttpUrl(item.url || item.href || item.path); %>
  <% const categories = Array.isArray(item.categories) ? item.categories : []; %>
  <% const primaryCategory = categories[0] || ""; %>
  <% const primarySlug = classToken(primaryCategory); %>
  <% const tags = Array.isArray(item.tags) ? item.tags : []; %>
  <% const domains = Array.isArray(item.hardware_domains) ? item.hardware_domains : []; %>
  <% const availabilityCandidate = String(item.artifact_availability || "unverified"); %>
  <% const availability = Object.prototype.hasOwnProperty.call(availabilityLabels, availabilityCandidate) ? availabilityCandidate : "unverified"; %>
  <article class="tool-card <%= primarySlug ? `tool-card-${primarySlug}` : "" %>" <%= metadataAttrs(item) %>>
    <div class="tool-card-link">
      <a class="tool-card-hitarea" href="<%= primaryUrl %>" target="_blank" rel="noopener" aria-label="Open <%= pandocSafe(item.title) %>"></a>
      <div class="tool-card-top">
        <h3 class="listing-title"><%= pandocSafe(item.title) %></h3>
        <span class="tool-card-arrow" aria-hidden="true">&nearr;</span>
      </div>
      <div class="tool-card-status" aria-label="Artifact availability and link verification">
        <span class="availability-badge availability-<%= availability %>"><%= availabilityLabels[availability] %></span>
        <span class="verification-date"><% if (item.last_verified) { %>Verified <%= pandocSafe(item.last_verified) %><% } else { %>Unverified<% } %></span>
      </div>
      <p class="listing-description"><%= pandocSafe(item.description) %></p>

      <% if (item.primary_metric) { %>
      <div class="benchmark-metric-box">
        <span class="benchmark-metric-label">Target metric:</span>
        <span class="benchmark-metric-val"><%= pandocSafe(item.primary_metric) %></span>
      </div>
      <% } %>

      <% if (item.health_audit_note) { %>
      <div class="benchmark-audit-box">
        <span class="benchmark-audit-label">Evaluation note:</span>
        <span class="benchmark-audit-text"><%= pandocSafe(item.health_audit_note) %></span>
      </div>
      <% } %>

      <% if (item.authors || item.institution) { %>
      <div class="tool-card-credit">
        <% if (item.authors) { %>
          <span><%= pandocSafe(item.authors) %></span>
        <% } %>
        <% if (item.institution) { %>
          <span><%= pandocSafe(item.institution) %></span>
        <% } %>
      </div>
      <% } %>

      <div class="listing-categories tool-card-categories">
        <% for (const category of categories) { %>
          <% const slug = classToken(category); %>
          <span class="tool-card-category <%= slug %>"><%= pandocSafe(category) %></span>
        <% } %>
        <% for (const domain of domains) { %>
          <span class="benchmark-domain-badge"><%= pandocSafe(domain) %></span>
        <% } %>
        <% for (const tag of tags) { %>
          <span class="tool-card-tag"><%= pandocSafe(tag) %></span>
        <% } %>
      </div>
    </div>
  </article>
<% } %>
</div>
```
