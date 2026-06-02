# Product

## Register

product

## Users

PacketScope is used by networking-course students during a final project presentation, and by a teacher who needs to understand the project quickly without reading the full report first. The user is usually in a classroom or demo setting, looking at one public website at a time and asking what actually happens between entering a URL and receiving a response.

## Product Purpose

PacketScope turns a public website URL into a live network checkup. It measures DNS lookup, TCP connection, TLS handshake, HTTP first-byte response, ping RTT, packet loss, and traceroute visibility from the PacketScope server, then explains the most visible bottleneck in plain language before showing technical evidence.

Success means a teacher can give the team a website, watch the tool perform real measurements, understand the network journey, and see that the project is more than a static report.

## Brand Personality

Clear, credible, instructional. The product should feel like a trustworthy observability workbench made for explaining networking concepts, not like a generic SaaS landing page or a decorative dashboard.

## Anti-references

- Generic AI SaaS pages with purple gradients, glass cards, and three identical feature cards.
- Dense monitoring dashboards that assume the user already understands every metric.
- Static report pages where the user cannot tell what action to take first.
- Decorative motion or visual effects that distract from the measurement workflow.
- Overly playful classroom visuals that make the tool feel less technically serious.

## Design Principles

1. Lead with the task: the first screen must make it obvious that the user should enter a public website and run a live check.
2. Explain before exposing evidence: start with a human-readable verdict, then show DNS/TCP/TLS/HTTP/ping/traceroute data.
3. Treat measurement location honestly: always state that online measurements come from the PacketScope server's vantage point.
4. Make the journey visible: represent the website visit as a sequence of network stages, not as disconnected numbers.
5. Keep failures meaningful: ping/traceroute restrictions and missing hops should be presented as diagnostic evidence, not hidden.

## Accessibility & Inclusion

Target WCAG AA contrast for text and controls. Keep English and Chinese UI copy readable at desktop and mobile widths. Respect reduced-motion preferences. Avoid color-only meaning in results and state indicators. Keep tables horizontally scrollable where needed, but provide the main verdict and timing cards before technical tables.
