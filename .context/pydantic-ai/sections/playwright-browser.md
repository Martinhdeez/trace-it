# [Playwright Browser](https://pydantic.dev/docs/ai/harness/playwright/)

> Give a Pydantic AI agent a real, stateful Chromium browser via async Playwright -- navigate, click, type, scroll, extract page text, run JavaScript, and screenshot JS-heavy or authenticated pages.

# Playwright Browser

`PlaywrightBrowser` gives an agent a real, stateful Chromium browser via async [Playwright](https://playwright.dev/python/): navigate, click, type, scroll, move through history, extract page text, run JavaScript, and screenshot.

Reach for it when the lighter web tools fall short. A web search tool answers a research question without loading a page, and a web-fetch tool handles a known static URL. This capability covers what neither can reach: pages behind login or session cookies, JavaScript-rendered SPAs, and interactive multi-step flows.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/playwright/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

Which browser capability?

This page covers driving the browser from the host model: typed, deterministic actions, one tool call at a time. To hand an open-ended goal to an autonomous agent that drives the browser for you, see [Browser Use](https://pydantic.dev/docs/ai/harness/browser-use/). Give an agent one or the other: each capability runs its own browser, so a session opened by one is not visible to the other.

## Installation

The `playwright` extra pulls in Playwright, and Chromium is a separate binary download:

-   [pip](#tab-panel-142)
-   [uv](#tab-panel-143)
-   [pip](#tab-panel-144)
-   [uv](#tab-panel-145)

Terminal

```bash
pip install "pydantic-ai-harness[playwright]"
```

Terminal

```bash
uv add "pydantic-ai-harness[playwright]"
```

Terminal

```bash
 playwright install chromium
```

Terminal

```bash
uv run playwright install chromium
```

If the Chromium binary is missing at runtime, the browser tool returns the `playwright install chromium` hint as its result rather than ending the run, so an agent that can run a shell can install the browser and carry on; the failure is not remembered, so the next call launches. The process also gets a `BrowserUnavailableWarning`, since a developer watching a terminal sees neither the tool result nor the trace. Set `auto_install_chromium=True` to fetch the binary automatically on the first miss instead.

## Usage

```python
from pydantic_ai import Agent
from pydantic_ai_harness.playwright import PlaywrightBrowser

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[PlaywrightBrowser()])
result = await agent.run('Open https://example.com and tell me the page title.')
```

`PlaywrightBrowser` is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/): it registers the browser toolset, injects short when-to-use guidance into the system prompt, and manages the Chromium lifecycle for the run.

## Tools

Tool

Signature

Returns

`navigate`

`(url, timeout_ms=None)`

page URL, title, and visible text (truncated)

`snapshot`

`(timeout_ms=None)`

the accessibility tree with `aria-ref` handles (truncated)

`click`

`(selector, timeout_ms=None)`

page text after the click; `selector` is a CSS selector, an `aria-ref=` handle, or `'x,y'` pixel coordinates

`type_text`

`(selector, text, sequential=False, timeout_ms=None)`

page text after typing (replaces the field value, does not submit); `sequential=True` sends real key presses

`press_key`

`(key, selector=None, timeout_ms=None)`

page text after the key press; `key` is a Playwright key name (`Enter`, `Escape`, `Tab`, `Control+a`)

`select_option`

`(selector, values, timeout_ms=None)`

page text after choosing options in a `<select>`

`hover`

`(selector, timeout_ms=None)`

page text after hovering, revealing hover-only menus

`wait_for`

`(selector=None, text=None, gone=False, timeout_ms=None)`

page text once the element/text appears -- or, with `gone=True`, once it is gone -- in the page or any frame; pass exactly one of `selector`/`text`

`screenshot`

`(full_page=False, timeout_ms=None)`

a note with the page URL, plus the PNG as image content

`get_text`

`(selector=None, timeout_ms=None)`

the element's text, or the full page's visible text

`scroll`

`(direction, x=None, y=None, timeout_ms=None)`

where the page now sits, and its text; `direction` is up/down/left/right (one screenful) or top/bottom

`go_back`

`(timeout_ms=None)`

the previous page's text

`go_forward`

`(timeout_ms=None)`

the next page's text

`execute_js`

`(script, timeout_ms=None)`

the JavaScript result (string as-is, objects as JSON, `null` as `undefined`)

`console_messages`

`(errors_only=False)`

console output and uncaught script errors, oldest first

`tabs`

`(action='list', index=None)`

the open tabs, or a confirmation plus the active tab's text; `action` is `list`/`select`/`close`/`new`

`handle_next_dialog`

`(accept, prompt_text=None)`

a confirmation of how the next `alert`/`confirm`/`prompt` will be answered

`network_requests`

`(url_contains=None, errors_only=False)`

requests the page made with their status, including ones the egress policy refused

Every page action accepts an optional `timeout_ms` to override both defaults for that one call. An override has to be greater than 0: `0` disables the deadline entirely, which stays available as a capability default but not as an argument the model picks.

A deadline bounds the whole tool call, not each Playwright call inside it. One `navigate` waits on a goto, a load state, a title, a body read and possibly a screenshot; each stage gets what is left of the budget rather than the whole number again, so `timeout_ms` is the longest the call can take.

Two defaults rather than one, because the two failures differ. An action that misses (`click`, `get_text`, `wait_for`) is normally a selector matching nothing, and `action_timeout_ms` (5s) turns that into a fast, readable failure instead of a wait long enough to read as a hung agent. A page load legitimately takes longer, so navigation, load settling, and starting or attaching to the browser use `navigation_timeout_ms` (60s).

`snapshot` returns the page's accessibility tree, the low-cost structured way for the model to read the page and obtain `aria-ref=eN` handles. Targeting an element by its `aria-ref=` handle (passed to `click` or `type_text`) is more reliable than a model-authored CSS selector. The snapshot includes iframe content (see [Embedded content](#embedded-content-iframes)). Reach for `screenshot` only when a visual check is needed (charts, layout).

`type_text` fills a field but does not submit it; `press_key('Enter')` does. A native `<select>` does not open as page content, so `select_option` operates it rather than `click`. `type_text` sets the value in one step and dispatches no key events, which is faster and enough for an ordinary form; pass `sequential=True` for a field that reacts to each keystroke -- autocomplete and type-ahead widgets, masked or formatted inputs, and editors that ignore a value set directly.

`wait_for` waits for content to arrive; `wait_for(gone=True)` waits for it to go away, which is how a spinner or an overlay is waited out when what replaces it is not known in advance.

Every tool acts on the active tab. A `target="_blank"` link, a sign-in popup or a payment step opens a second one, which stays open rather than being closed: `tabs('list')` shows what is open and `tabs('select', index)` moves there. A session keeps up to eight tabs: past that, a tab the page opens is closed and recorded, while `tabs('new')` is refused and asks the model to close one first. A page dialog (`alert`, `confirm`, `prompt`) blocks the page until it is answered, and is dismissed unless `handle_next_dialog(accept=True)` was called before the action that opened it -- that call covers one dialog, not the rest of the run.

`screenshot` (and the optional `screenshot_on_navigate` attachment) return the image as [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) rather than a base64 string, so vision models see the image natively instead of a wall of base64 in the text context. A capture over 5 MB (typically a full-page screenshot of a long page) is returned as a bounded error instead of image content, because model providers reject oversized images and the failure would otherwise abort the run; capture the viewport or scroll and capture sections instead.

Browser tool failures -- a timeout, a selector that matches no element, a navigation error, or a browser that closed mid-run -- are returned to the model as error strings it can act on (retry, try another selector, navigate again), not raised to abort the agent run.

## Options

Option

Default

Purpose

`headless`

`True`

Run Chromium without a visible window (suits servers and CI).

`allowed_domains`

`None`

Egress allowlist for navigation and data requests; `None` allows every public host (see [Egress](#egress-and-ssrf)).

`policy`

`None`

Full `EgressPolicy`, for rules the two shorthands cannot express. Mutually exclusive with them.

`block_private_addresses`

`True`

Refuse private, loopback, link-local and other reserved addresses, whether written as an IP or reached through a hostname that resolves to one (see [Egress](#egress-and-ssrf)).

`screenshot_on_navigate`

`False`

Attach a screenshot to every `navigate` result.

`max_content_tokens`

`4000`

Approximate token budget for every textual tool result.

`action_timeout_ms`

`5000`

Default deadline for element actions (click, type, read, wait). `0` disables it.

`navigation_timeout_ms`

`60000`

Default deadline for navigation and load settling, and for starting or attaching to the browser. `0` disables it.

`chromium_sandbox`

`True`

Run the launched Chromium with its renderer sandbox. Turn it off only where the sandbox cannot start (a container without the kernel privileges it needs). Ignored with `cdp_url`.

`auto_install_chromium`

`False`

Fetch Chromium automatically when the binary is missing.

`storage_state`

`None`

Playwright storage state (cookies + localStorage) loaded at launch; see [Authenticated sites](#authenticated-sites).

`cdp_url`

`None`

Attach to a Chromium already running at this CDP endpoint instead of launching one; see [Attaching to a running browser](#attaching-to-a-running-browser).

## Authenticated sites

Pass `storage_state` to start the browser already logged in. It is a Playwright [storage state](https://playwright.dev/python/docs/auth) object -- cookies plus localStorage -- loaded into the browser context at launch, so the first navigation is already authenticated.

Capture it once, in your own code, by logging in with a visible browser:

```python
from playwright.async_api import async_playwright


async def capture_state() -> object:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://example.com/login')
        # Log in by hand in the window that opened. The capture waits for a page
        # only a signed-in session reaches, so it runs after the login rather than
        # racing it; the deadline is long because a person is typing.
        await page.wait_for_url('https://example.com/account', timeout=300_000)
        state = await context.storage_state()
        await browser.close()
        return state
```

`playwright codegen https://example.com --save-storage=auth.json` writes the same structure to a file, which you load with `json.loads(Path('auth.json').read_text())`. Either way, hand the object to the capability:

```python
from pydantic_ai import Agent
from pydantic_ai_harness.playwright import PlaywrightBrowser

state = ...  # captured above

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        PlaywrightBrowser(storage_state=state, allowed_domains=['example.com']),
    ],
)
```

The option takes an object rather than a path because agents commonly run in shared environments where the local filesystem is not somewhere to put anything durable: where the state lives is your decision, not the capability's. For the same reason `PlaywrightBrowser.from_spec` does not accept `storage_state` -- a spec would carry the cookies into whatever stores it. Set it on the constructed capability instead.

The capability runs headless by default and does not drive the login flow itself: you capture the state out of band. The usual pattern is to log in once with a visible browser, then reuse the state for headless runs.

Treat the state as credential material: it can impersonate the account. Keep it out of source control and out of logs, store it with restrictive permissions if you do persist it, and discard it when the session expires. This mirrors Playwright's own [auth-guide](https://playwright.dev/python/docs/auth) warning. Prefer a minimal-scope state (log in to only the target site when capturing it) over reusing a full browser profile.

## Attaching to a running browser

Set `cdp_url` to connect to a Chromium that is already running at a [Chrome DevTools Protocol](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp) endpoint instead of launching one:

```python
from pydantic_ai import Agent
from pydantic_ai_harness.playwright import PlaywrightBrowser

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[PlaywrightBrowser(cdp_url='http://localhost:9222')],
)
```

No local Chromium binary is involved, so the install hint and `auto_install_chromium` do not apply. This is what managed-browser providers and benchmark harnesses expect: they start a browser and hand you its endpoint.

The run still gets its own browser context, so `storage_state`, the domain allowlist, and the private-address block apply exactly as they do for a launched browser, and the agent does not inherit the sessions already open in that Chrome. Pointing `cdp_url` at your personal everyday browser is still the higher-risk choice -- that process holds every account you are logged into, and anything the agent can reach through it is reachable in one prompt injection. Prefer a browser started for the agent, with a scoped `storage_state`. Provider endpoints sometimes embed an auth token in the URL; treat those as secrets.

## Lifecycle

Chromium starts lazily on the first browser-tool call and is closed when the run ends -- on success, error, or cancellation. Runs that never call a browser tool pay no Playwright cost (no subprocess, no window). Each agent run gets its own page and browser, so concurrent `agent.run()` calls never share a tab.

That lifecycle lives in `PlaywrightBrowserSession`, which the capability creates per run. It is exported for the case where you want the same guarded browser without an agent around it -- the allowlist, the private-address block, the service-worker block, the tab tracking, and the dialog handling all come with it:

```python
from pydantic_ai_harness.playwright import PlaywrightBrowserSession

async with PlaywrightBrowserSession() as session:
    page = await session.ensure_page()  # Chromium starts here, not on entry
    await page.goto('https://example.com')
```

`PlaywrightBrowserToolset` is exported on the same basis: pass it a session to get the eighteen tools without the capability's hooks. The policy lives on the session and only there, so the guard the session installs and the checks the tools run cannot diverge: they are two layers of one decision, applied at different moments.

## Embedded content (iframes)

Page-level selectors stop at the frame boundary, so an embedded schedule, checkout step, or chat widget is not reachable through a CSS selector, and a page that is mostly an embed can look almost empty. The capability closes that gap in three places:

-   Tools that return page text (`navigate`, `click`, `get_text` without a selector, and the rest) append the text of each child frame that has any, inside the same token budget.
-   `wait_for` watches the page and every child frame at once; the first match wins.
-   `snapshot` includes frame content, and its refs carry the frame they came from (`f1e4` rather than `e4`). Passing such a ref to `click`, `type_text`, `hover` or `get_text` resolves inside that frame -- the one handle that reaches embedded content.

The sweep over child frames is bounded, so one unresponsive embed cannot consume the action's deadline; whatever the other frames returned is kept.

## Debugging a run

Three things make a browser agent hard to follow: the page is invisible, a missing element looks the same as a slow one, and the interesting failures happen between tool calls.

-   Set `headless=False` to watch the run in a real window.
-   Every browser operation opens an OpenTelemetry span named `browser <action>` (`browser click`, `browser navigate`), carrying `browser.action`, `browser.timeout_ms`, `browser.outcome`, and the resulting `url.full`. What the page did during that operation is attached as span events: console output, uncaught script errors, responses, requests the egress policy refused, dialogs the page opened, and tabs it opened. The spans go to the run's own tracer, so an agent instrumented for [Logfire](https://pydantic.dev/docs/ai/integrations/logfire/) reports them with everything else.
-   The agent can read the same log through `console_messages` and `network_requests`, which is often how it recovers from a page that renders from an API rather than from HTML. Only what identifies a request is recorded, never a response body. A busy page produces more entries than fit the token budget, and it is the oldest that are dropped, so the failure that prompted the call survives; `network_requests(errors_only=True)` narrows it further. Recorded URLs keep their host, path and parameter names but lose `user:password@` credentials and the values of credential-bearing parameters (`token`, `code`, `signature`, and the rest), since those reach both the model and the telemetry backend.
-   A wait that seems to hang is usually an action timeout. `action_timeout_ms` defaults to 5s so the failure arrives quickly; lower it further while debugging, and read the timeout value in the error string to tell a slow page from a wrong selector.

Logfire's default scrubbing redacts values matching patterns such as `session`, `auth`, `cookie` and `credit card`, which match page content more often than you would expect -- a conference site whose every heading says "session" comes back as `[Scrubbed due to 'session']`, and a pricing page as `[Scrubbed due to 'credit card']`. Keep tool results readable by scrubbing them selectively:

```python
import re

import logfire

# The words Logfire redacts on that are ordinary vocabulary on a public page.
page_words = {'session', 'cookie', 'credit card', 'auth'}


def keep_browser_results(match: logfire.ScrubMatch) -> str | None:
    # 'tool_response' is the same attribute under instrumentation version 2
    if match.path[:2] not in {('attributes', 'gen_ai.tool.call.result'), ('attributes', 'tool_response')}:
        return None
    matched = re.sub(r'[._\- ]+', ' ', match.pattern_match.group(0)).strip().lower()
    return match.value if matched in page_words else None


logfire.configure(scrubbing=logfire.ScrubbingOptions(callback=keep_browser_results))
```

Returning `match.value` keeps the original text; returning `None` leaves the redaction in place. The callback is given the attribute, not the tool that produced it, so it cannot be limited to the browser's results -- narrowing on the word that triggered the redaction is what keeps `password`, `api_key` and `jwt` redacted whichever tool returned them.

## Limitations

-   A session keeps up to eight tabs open; a page that opens more has the extras closed, which is recorded in the event log.
-   Uploads and downloads are not exposed: the context refuses downloads, and there is no tool to put a file into a page. Both need an artifact contract between the page and the host filesystem, tracked in [#590](https://github.com/pydantic/pydantic-ai-harness/issues/590).
-   CSS selectors cannot reach content inside iframes; reading and acting there goes through `snapshot` refs (see [Embedded content](#embedded-content-iframes)).
-   Durable execution (e.g. `TemporalDurability`) is rejected at agent construction: a live Chromium page cannot survive activity replay or worker restart.
-   The model targets elements by `aria-ref=` handle (from `snapshot`), CSS selector, or pixel coordinates.

## Egress and SSRF

By default the browser refuses addresses that are not globally routable -- `169.254.169.254` (the cloud metadata endpoint), `127.0.0.1`, `::1`, `localhost` and `*.localhost` names, and the RFC 1918 private ranges -- even when no allowlist is set. A hostname is resolved first, so pointing a name at one of those addresses does not get past it. Set `block_private_addresses=False` when the agent should reach a local app or an internal dashboard.

With `allowed_domains=None` (the default) the agent can reach any public URL. When the agent may act on untrusted input, set `allowed_domains` to an explicit allowlist. Each entry matches its exact host and any subdomain -- `example.com` reaches `api.example.com` -- compared in the ASCII form Chromium itself uses, so an internationalized host and its `xn--` spelling get the same verdict. An entry written as a wildcard (`*.example.com`) raises at construction: it would match no host at all, while reading like a configured allowlist.

How far the allowlist reaches depends on what the request is for:

Request

Bounded by `allowed_domains`

Top-level navigation

yes

`fetch`, XHR, EventSource, WebSocket, `sendBeacon`

yes

Images, stylesheets, scripts, fonts, media

no

Sub-frame documents

no

Data requests are included because a script on a permitted page can otherwise read from, or post to, anywhere; passive subresources and sub-frame documents are not, because a page whose assets are aborted renders as a broken page and a permitted site's identity-provider and payment steps live in frames. The private-address block ignores that split entirely: it applies to every frame and every resource type. WebSocket connections, which a network route never sees, get their own guard, applying the same policy the table above describes.

A host that is not already an address is resolved before the private-address block classifies it, so a name pointing at an internal address (`169.254.169.254.nip.io` and similar wildcard DNS services) is refused rather than followed. That lookup runs for every kind, matching the literal check, so a spelling does not decide the verdict; answers are cached, which makes it a lookup per distinct host rather than per request. `resolved_kinds` sets which kinds are looked up.

A lookup that does not answer within two seconds is a refusal, not an allow: whoever controls a name controls whether its lookup answers, so a stall would otherwise be a way past the block. The cost of that is small when the failure is honest, since a name this process cannot resolve is one the browser is about to fail on too. None of this is proof against DNS rebinding: Chromium resolves the name a second time before it connects, and a record that changes in between defeats it. The policies are independent and deny wins -- an allowlisted private address is still refused until you opt out of `block_private_addresses`.

Enforcement is at two layers: a network route guard aborts a refused request before it leaves (covering clicks, `execute_js`, and history moves, not just `navigate`), and each tool re-checks the resulting URL and bounces to `about:blank` so disallowed content never reaches the model. Service workers are blocked in the browser context so their traffic cannot slip past the route guard.

### Rules the two fields cannot express

`EgressPolicy` is the whole policy, and `PlaywrightBrowser(policy=...)` takes one instead of the `allowed_domains` / `block_private_addresses` shorthands. Its fields cover a denylist (`blocked_domains`, which wins over everything and reaches every request kind), apex-only matching (`include_subdomains=False`), and which kinds the allowlist bounds (`allowlist_reach`).

```python
from typing import get_args

from pydantic_ai_harness.playwright import EgressPolicy, PlaywrightBrowser, RequestKind

# Nothing leaves for a host outside the list, whatever the request is for.
locked_down = EgressPolicy(
    allowed_domains=['example.com'],
    allowlist_reach=frozenset(get_args(RequestKind)),
)

browser = PlaywrightBrowser(policy=locked_down)
```

For a decision the fields do not describe, subclass and override `refuse`. It is given the URL, the kind, Playwright's own `resource_type`, the method, and whether the request is the main frame's own document:

```python
from pydantic_ai_harness.playwright import EgressPolicy, EgressRequest


class FontsFromAnywhere(EgressPolicy):
    def refuse(self, request: EgressRequest) -> str | None:
        if request.resource_type == 'font':
            return None
        return super().refuse(request)
```

Returning `None` allows the request; returning a string refuses it and records that string as the reason, which the model can read through `network_requests`. An override that narrows what `refuse` allows should override `describe` too: `describe` is what the model is told about its reach, and it reads only the fields.

Neither policy is a general security boundary. Microsoft's own playwright-mcp disclaims its origin filter the same way. A page can still signal outward through the request kinds the allowlist leaves alone -- an image or script URL carries whatever the page puts in it -- and a hostname is classified on the answer this process gets, while Chromium resolves it again before connecting, so a record that changes in between (DNS rebinding) still wins. That, and the proxy-based enforcement mode which is what closes it, are tracked in [#415](https://github.com/pydantic/pydantic-ai-harness/issues/415).

For untrusted-input scenarios, run the browser in a container or VM with an egress firewall, or front it with a proxy, and pair it with the harness's tool-approval hooks for consequential actions. Treat these as defense in depth, not a guarantee.

## Further reading

-   [Browser automation with Pydantic-AI + Playwright](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/browser-automation-with-pydantic-ai--playwright/4547971) (Microsoft) -- this capability driving a manual QA pass over a live site, wired to Microsoft Foundry models, with the run's OpenTelemetry traces.
-   [Browser Use](https://pydantic.dev/docs/ai/harness/browser-use/) -- the other browser capability. Each runs its own browser, so give an agent one or the other.
-   [Playwright for Python](https://playwright.dev/python/) -- the automation library underneath, and the reference for selector syntax.
-   [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)

## API reference

### PlaywrightBrowser

**Bases:** `AbstractCapability[AgentDepsT]`

A real, stateful Chromium browser for an agent, via async Playwright.

Adds eighteen tools -- navigate, snapshot, click, type\_text, press\_key, select\_option, hover, wait\_for, screenshot, get\_text, scroll, go\_back, go\_forward, execute\_js, tabs, handle\_next\_dialog, console\_messages, network\_requests -- backed by a Chromium context that persists across tool calls within a run. Reach for it when the lighter web tools fall short: pages behind login/session cookies, JavaScript-rendered SPAs, and interactive multi-step flows. For query-based research prefer a web-search tool; for a static URL prefer a web-fetch tool.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.playwright import PlaywrightBrowser

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[PlaywrightBrowser()])
```

Requires the `playwright` optional extra and the Chromium binary:

Terminal

```bash
pip install 'pydantic-ai-harness[playwright]'
playwright install chromium
```

Egress: `allowed_domains=None` (the default) places no domain restriction on the URLs the agent can reach; pass `allowed_domains=[...]` to bound navigation and the request kinds that move data (`fetch`, XHR, EventSource, WebSocket, `sendBeacon`) in any frame, leaving passive subresources and sub-frame documents unbounded so a permitted page keeps its assets and its identity-provider frames. Independently, `block_private_addresses=True` (the default) refuses private, loopback, link-local and other reserved addresses for every request kind in every frame, even under open egress, resolving a hostname first so a name pointing at one of those addresses is refused too. Neither is a general security boundary: an unanswered DNS lookup is refused but Chromium resolves the name again before it connects, so rebinding is not closed, and a proxy-based enforcement mode is tracked in [https://github.com/pydantic/pydantic-ai-harness/issues/415](https://github.com/pydantic/pydantic-ai-harness/issues/415). Set `allowed_domains` when the agent may act on untrusted input.

Chromium starts lazily on the first browser-tool call and is closed when the run ends (on success, error, or cancellation); runs that never call a browser tool pay no Playwright cost. When no browser can be started the tool returns a `playwright install chromium` hint instead of ending the run, so an agent that can run a shell can install it and carry on, and the process gets a `BrowserUnavailableWarning` for the developer who is not reading tool results. Set `auto_install_chromium=True` to fetch the binary automatically instead. Set `cdp_url` to attach to a Chromium that is already running (managed-browser providers, benchmark harnesses) rather than launching one.

Every browser operation runs inside an OpenTelemetry span, and what the page did during it (console output, responses, requests the egress policy refused, dialogs it opened, tabs it opened) is attached to that span as span events and readable by the agent through `console_messages` and `network_requests`.

Durable execution (e.g. `TemporalDurability`) is not supported: durability replays tool calls as activities and a live Chromium page cannot survive replay or worker restart, so combining both on one agent raises `UserError` at agent construction.

#### Attributes

##### headless

Run Chromium without a visible window. `True` suits servers and CI.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### allowed\_domains

Egress allowlist. `None` (default) allows every public host -- see the egress note above.

Each entry matches its exact host and any subdomain, so `example.com` reaches `api.example.com`. It bounds top-level navigation and the requests a page's scripts use to move data (`fetch`, XHR, EventSource, WebSocket, `sendBeacon`); passive subresources and sub-frame documents are left alone, so a permitted page keeps its CDN assets and its identity-provider frames. Enforced at two layers: a network route guard aborts a refused request before it leaves, and each tool re-checks the resulting URL and bounces to `about:blank` so disallowed content never reaches the model.

For anything this does not express -- a denylist, apex-only matching, locking down every request type, a rule of your own -- pass an `EgressPolicy` as `policy` instead.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### policy

Full egress policy, for rules the two shorthands above cannot express.

Mutually exclusive with `allowed_domains` and `block_private_addresses`, which build the default policy when this is unset. Subclass `EgressPolicy` and override `refuse` for a decision the fields do not cover. Absent from `from_spec`, since a policy can carry arbitrary code.

**Type:** `EgressPolicy` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### block\_private\_addresses

Refuse addresses that are not globally routable, for every request kind in every frame.

Covers the cloud metadata endpoint (`169.254.169.254`), loopback (`127.0.0.1`, `::1`, `localhost`), and the RFC 1918 ranges, independent of `allowed_domains` -- open egress still cannot reach them. A hostname is resolved first, so a name pointing at one of those addresses is refused too, as is one whose lookup does not answer (see the egress note above). Set `False` when the agent should reach a local app or an internal dashboard.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### screenshot\_on\_navigate

Attach a screenshot (as image content) to every `navigate` result.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### max\_content\_tokens

Approximate token budget for textual tool results.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_MAX_CONTENT_TOKENS`

##### action\_timeout\_ms

Default deadline for element actions (click, type, read, wait), in milliseconds.

Shorter than the navigation budget on purpose. An action that misses is normally a selector matching nothing, and a long deadline makes that look like a hung agent rather than a fast failure the model can react to. Raise it for pages whose elements appear slowly.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_ACTION_TIMEOUT_MS`

##### navigation\_timeout\_ms

Default deadline for navigation and load settling, and for starting or attaching to the browser, in milliseconds.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_NAVIGATION_TIMEOUT_MS`

##### chromium\_sandbox

Run the launched Chromium with its renderer sandbox.

On by default, unlike Playwright itself: this capability opens pages nobody vetted, and the sandbox is what keeps a renderer that a crafted page compromises from reaching the host. Set `False` where the sandbox cannot start -- a container without the kernel privileges it needs is the usual case -- and accept that a renderer exploit then runs with the agent's own access. Ignored when `cdp_url` is set: that browser is already running under its own configuration.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### auto\_install\_chromium

Fetch the Chromium binary via `playwright install chromium` on the first miss.

Off by default: a library should not download a browser as a side effect. When the binary is missing the browser tool returns a clear install hint, which an agent that can run a shell can act on. Set `True` to opt into the automatic download instead.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### storage\_state

Playwright storage state (cookies, localStorage) loaded into the browser context at launch.

Obtain it in your own code -- `await context.storage_state()`, or `json.loads(Path('auth.json').read_text())` for a file written by `playwright codegen --save-storage` -- so the login runs where you control it and the credentials never have to reach wherever the agent runs. This is session material equivalent to the account: keep it out of source control and out of logs, and discard it when the session expires.

An object rather than a path so the capability never assumes a filesystem it can read: agents often run where the local disk is neither durable nor writable, so where the state lives stays the caller's decision. For the same reason `from_spec` does not accept it.

**Type:** `StorageState` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

##### cdp\_url

Attach to a Chromium already running at this Chrome DevTools Protocol endpoint.

When set, the capability connects instead of launching, so no local Chromium binary is needed and `auto_install_chromium` does not apply. Used for managed-browser providers and benchmark harnesses that hand the agent a browser. A new browser context is still created for the run, so `storage_state` and the egress guards apply as they do for a launched browser, and the run does not inherit the sessions already open in that Chrome. Provider endpoints sometimes carry an auth token in the URL; treat those as secrets.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

#### Methods

##### for\_agent

```python
def for_agent(
    agent: AbstractAgent[AgentDepsT, object],
) -> AbstractCapability[AgentDepsT]
```

Refuse to bind to a durable-execution agent.

Durable execution (e.g. `TemporalDurability`) wraps the toolsets captured at agent construction and replays tool calls as activities. A live Chromium page cannot be checkpointed across activity boundaries or worker restarts, so the composition cannot work; without this guard it fails deep inside the first browser tool call instead.

Detection matches `BaseDurabilityCapability`, the shared base of the bundled Temporal/DBOS/Prefect integrations. Pydantic AI exposes no public marker for the durability tier, and the `innermost` ordering position is not one: `InputGuard` also declares `innermost`, so ordering alone would reject the supported guard-plus-browser composition.

###### Returns

`AbstractCapability`\[`AgentDepsT`\]

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> PlaywrightBrowser[AgentDepsT]
```

Return a fresh instance per run so concurrent runs never share a page or browser.

###### Returns

`PlaywrightBrowser`\[`AgentDepsT`\]

##### get\_toolset

```python
def get_toolset() -> PlaywrightBrowserToolset[AgentDepsT]
```

Provide the eighteen browser tools.

###### Returns

`PlaywrightBrowserToolset`\[`AgentDepsT`\]

##### get\_instructions

```python
def get_instructions() -> Callable[[RunContext[AgentDepsT]], str | None]
```

When-to-use guidance for the browser.

###### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)\]

##### wrap\_run

`@async`

```python
def wrap_run(
    ctx: RunContext[AgentDepsT],
    *,
    handler: WrapRunHandler,
) -> AgentRunResult[Any]
```

Hold the run's browser session open, and release it however the run ends.

Chromium starts on the first browser-tool call, not here, so a run that never browses never launches one. The run's tracer is adopted here so browser spans follow the agent's instrumentation settings rather than a tracer of this module's choosing.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    headless: bool = True,
    allowed_domains: list[str] | None = None,
    block_private_addresses: bool = True,
    screenshot_on_navigate: bool = False,
    max_content_tokens: int = DEFAULT_MAX_CONTENT_TOKENS,
    action_timeout_ms: int = DEFAULT_ACTION_TIMEOUT_MS,
    navigation_timeout_ms: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
    auto_install_chromium: bool = False,
    chromium_sandbox: bool = True,
    cdp_url: str | None = None,
) -> PlaywrightBrowser[AgentDepsT]
```

Construct the capability from serializable spec options (all fields are plain scalars/lists).

A spec carries connection configuration, not session credentials: `storage_state` is deliberately absent, so a spec naming it raises rather than moving cookies into whatever stores the spec. Set it on the constructed capability instead.

###### Returns

`PlaywrightBrowser`\[`AgentDepsT`\]

---
